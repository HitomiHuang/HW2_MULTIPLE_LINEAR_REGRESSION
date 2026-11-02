"""HW2: CRISP-DM multiple linear regression, feature selection, and intervals.

Run: python 5113056021_hw2.py
Predict: python 5113056021_hw2.py --predict data/new_samples.csv
The default run is offline and uses the supplied Kaggle train.csv.
Only the proper training split is used for model/feature selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

# Bound BLAS/OpenMP threads for reproducibility on laptops and shared computers.
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_name, "2")
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / "tmp" / "matplotlib"))

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy import stats
import sklearn
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.feature_selection import RFE, SelectKBest, f_regression
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import statsmodels
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson, jarque_bera
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parent
TARGET = "FloodProbability"
SEED = 42
FEATURES = [
    "MonsoonIntensity", "TopographyDrainage", "RiverManagement", "Deforestation",
    "Urbanization", "ClimateChange", "DamsQuality", "Siltation",
    "AgriculturalPractices", "Encroachments", "IneffectiveDisasterPreparedness",
    "DrainageSystems", "CoastalVulnerability", "Landslides", "Watersheds",
    "DeterioratingInfrastructure", "PopulationScore", "WetlandLoss",
    "InadequatePlanning", "PoliticalFactors",
]
BLUE, GOLD, INK = "#2864A0", "#C48B20", "#273445"


def save_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def pipeline(selector=None, estimator=None):
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("select", selector if selector is not None else "passthrough"),
        ("model", estimator if estimator is not None else LinearRegression()),
    ])


def metrics(y, pred, p=None):
    r2 = float(r2_score(y, pred))
    return {
        "MAE": float(mean_absolute_error(y, pred)),
        "MSE": float(mean_squared_error(y, pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y, pred))),
        "R2": r2,
        # Descriptive holdout adjustment; not an unbiased model-selection criterion.
        "Adjusted_R2": 1 - (1-r2)*(len(y)-1)/(len(y)-p-1) if p is not None else None,
    }


def plot_style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 13,
        "axes.labelcolor": INK, "text.color": INK, "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "grid.alpha": .16,
        "figure.facecolor": "white", "savefig.facecolor": "white", "axes.axisbelow": True,
    })


def save_fig(fig, path):
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def make_figures(out, X_train, y_train, selection, results, preds, fitted, coef):
    plot_style()
    fig, ax = plt.subplots(figsize=(8.4, 3.2), layout="constrained")
    ax.hist(y_train, bins=35, color=BLUE, edgecolor="white")
    ax.set(title="Training target distribution", xlabel="FloodProbability (synthetic score)", ylabel="Count")
    ax.text(.98,.95,f"Proper training n = {len(y_train):,}",transform=ax.transAxes,ha="right",va="top")
    save_fig(fig, out/"01_target_distribution.png")

    corr = X_train.corr()
    fig, ax = plt.subplots(figsize=(8.4, 6.5), layout="constrained")
    im = ax.imshow(corr, cmap="Blues", vmin=-1, vmax=1)
    ax.set_xticks(range(20), FEATURES, rotation=90, fontsize=7)
    ax.set_yticks(range(20), FEATURES, fontsize=7)
    ax.set_title("Predictor correlations | proper training only")
    fig.colorbar(im, ax=ax, shrink=.65, label="Pearson correlation")
    ax.grid(False)
    save_fig(fig, out/"02_correlations.png")

    fig, ax = plt.subplots(figsize=(8.4, 3.8), layout="constrained")
    ax.errorbar(selection.k, selection.cv_rmse, yerr=selection.cv_std, color=BLUE, marker="o", capsize=3)
    ax.set(title="Feature selection | 5-fold training CV", xlabel="Number of selected original features", ylabel="CV RMSE (mean +/- fold SD)")
    ax.set_xticks(selection.k)
    save_fig(fig, out/"03_feature_selection.png")

    fig, ax = plt.subplots(figsize=(8.4, 4.0), layout="constrained")
    r=results.sort_values("RMSE",ascending=False)
    ax.barh(r.model, r.RMSE, color=[GOLD if v=="OLS_selected" else BLUE for v in r.model], edgecolor=INK,linewidth=.4)
    for i,val in enumerate(r.RMSE): ax.text(val+.00025,i,f"{val:.4f}",va="center",fontsize=9)
    ax.set(title="Holdout prediction error | n = 10,000",xlabel="RMSE (lower is better)",xlim=(0,r.RMSE.max()*1.17))
    save_fig(fig, out/"04_model_comparison.png")

    shown=preds.sample(min(2500,len(preds)),random_state=SEED)
    fig, ax=plt.subplots(figsize=(6.5,5.4),layout="constrained")
    ax.scatter(shown.actual,shown.prediction,s=9,alpha=.20,color=BLUE,edgecolors="none")
    ax.plot([.25,.75],[.25,.75],"--",color=INK,lw=1.2,label="Ideal prediction")
    ax.set(title="OLS: actual vs predicted",xlabel="Actual synthetic score",ylabel="Predicted score",xlim=(.25,.75),ylim=(.25,.75))
    ax.set_aspect("equal"); ax.legend(frameon=False)
    save_fig(fig,out/"05_actual_vs_prediction.png")

    # Deterministic random cases, then ordered by prediction: not a time series.
    shown=preds.sample(120,random_state=SEED).sort_values("prediction").reset_index(drop=True)
    fig, ax=plt.subplots(figsize=(8.4,4.3),layout="constrained")
    x=np.arange(len(shown))
    ax.fill_between(x,shown.conformal_lower,shown.conformal_upper,color=BLUE,alpha=.15,label="95% split-conformal PI")
    ax.plot(x,shown.prediction,color=BLUE,lw=1.5,label="OLS prediction")
    ax.scatter(x,shown.actual,color=GOLD,s=15,edgecolors=INK,linewidths=.25,label="Observed target",zorder=3)
    ax.set(title="Predictions with 95% prediction intervals",xlabel="120 holdout cases, sorted by prediction (not time)",ylabel="FloodProbability (synthetic score)")
    ax.legend(loc="upper left",frameon=False,fontsize=8)
    save_fig(fig,out/"06_prediction_intervals.png")

    residual=np.asarray(fitted.resid)
    fig,axes=plt.subplots(1,2,figsize=(8.4,3.4),layout="constrained")
    take=np.random.default_rng(SEED).choice(len(residual),min(4000,len(residual)),replace=False)
    axes[0].scatter(np.asarray(fitted.fittedvalues)[take],residual[take],s=5,alpha=.16,color=BLUE)
    axes[0].axhline(0,color=INK,lw=1,ls="--")
    axes[0].set(title="Training residuals",xlabel="Fitted score",ylabel="Residual")
    (qqx,qqy),(slope,intercept,_)=stats.probplot(residual,dist="norm")
    stride=max(1,len(qqx)//2000)
    axes[1].scatter(qqx[::stride],qqy[::stride],s=6,color=BLUE,alpha=.5)
    axes[1].plot(qqx,slope*qqx+intercept,color=INK,lw=1,ls="--")
    axes[1].set(title="Residual normal Q-Q",xlabel="Theoretical normal quantile",ylabel="Ordered residual")
    save_fig(fig,out/"07_diagnostics.png")

    c=coef.loc[coef.feature!="const"].sort_values("coefficient")
    fig,ax=plt.subplots(figsize=(8.4,5.8),layout="constrained")
    ax.errorbar(c.coefficient,np.arange(len(c)),xerr=[c.coefficient-c.hc3_lower,c.hc3_upper-c.coefficient],fmt="o",color=BLUE,capsize=2,ms=3)
    ax.set_yticks(range(len(c)),c.feature,fontsize=8)
    ax.axvline(0,color=INK,lw=1)
    ax.set(title="Standardized OLS coefficients | HC3 95% CI",xlabel="Score change per 1 SD of predictor (conditional association)")
    save_fig(fig,out/"08_coefficients.png")


def predict_new(args):
    bundle=joblib.load(args.output/"models"/"ols_bundle.joblib")
    frame=pd.read_csv(args.predict)
    missing=set(FEATURES)-set(frame.columns)
    if missing: raise ValueError(f"Missing predictors: {sorted(missing)}")
    values=frame[FEATURES].apply(pd.to_numeric,errors="raise")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError("New cases must contain finite numeric values for all 20 features.")
    pred=bundle["pipeline"].predict(values)
    X=bundle["pipeline"][:-1].transform(values)
    sf=bundle["ols"].get_prediction(sm.add_constant(X,has_constant="add")).summary_frame(alpha=.05)
    output=pd.DataFrame({"prediction":pred,"mean_ci_lower":sf.mean_ci_lower,"mean_ci_upper":sf.mean_ci_upper,
                         "ols_pi_lower":sf.obs_ci_lower,"ols_pi_upper":sf.obs_ci_upper,
                         "conformal_lower":pred-bundle["conformal_q"],"conformal_upper":pred+bundle["conformal_q"]})
    bounds=bundle["training_bounds"]
    output["outside_training_range"]=((values<bounds["min"])|(values>bounds["max"])).any(axis=1).to_numpy()
    dest=args.output/"new_predictions.csv"; output.to_csv(dest,index=False)
    print(f"Saved {dest}")
    return output


def run_analysis(data=ROOT/"data"/"train.csv",output=ROOT/"output",sample_size=50000):
    output=Path(output)
    for d in [output,output/"tables",output/"figures",output/"models"]: d.mkdir(parents=True,exist_ok=True)
    print("[1/7] Reading the supplied Kaggle competition training file",flush=True)
    raw=pd.read_csv(data)
    if set(raw.columns)!=set(FEATURES+[TARGET,"id"]): raise ValueError("Unexpected source schema")
    sample=raw.sample(n=min(sample_size,len(raw)),random_state=SEED).copy()
    if sample["id"].duplicated().any(): raise ValueError("Duplicate row ids")
    if sample[FEATURES+[TARGET]].isna().any().any(): raise ValueError("Unexpected missing values: review before modeling")
    if not np.isfinite(sample[FEATURES+[TARGET]].to_numpy()).all(): raise ValueError("Non-finite data")
    if not sample[TARGET].between(0,1).all(): raise ValueError("Target outside [0,1]")
    X,y=sample[FEATURES],sample[TARGET]
    proper_cal,test=train_test_split(sample.index,test_size=.20,random_state=SEED)
    proper,cal=train_test_split(proper_cal,test_size=.20,random_state=SEED)
    X_train,y_train=X.loc[proper],y.loc[proper]
    X_cal,y_cal=X.loc[cal],y.loc[cal]
    X_test,y_test=X.loc[test],y.loc[test]
    split=pd.DataFrame({"id":sample.id,"split":""})
    split.loc[proper,"split"]="proper_train";split.loc[cal,"split"]="calibration";split.loc[test,"split"]="test"
    split.to_csv(output/"tables"/"split_manifest.csv",index=False)
    X_train.describe().T.to_csv(output/"tables"/"training_descriptives.csv")
    sample.to_csv(output/"tables"/"analysis_sample.csv",index=False)
    cv=KFold(n_splits=5,shuffle=True,random_state=SEED)

    print("[2/7] Training-only feature selection and Ridge tuning",flush=True)
    select_search=GridSearchCV(pipeline(SelectKBest(f_regression)),{"select__k":list(range(14,21))},
                              scoring="neg_root_mean_squared_error",cv=cv,n_jobs=1,refit=True)
    select_search.fit(X_train,y_train)
    cvtab=pd.DataFrame({"k":[d["select__k"] for d in select_search.cv_results_["params"]],
                        "cv_rmse":-select_search.cv_results_["mean_test_score"],"cv_std":select_search.cv_results_["std_test_score"]})
    cvtab.to_csv(output/"tables"/"feature_selection_cv.csv",index=False)
    chosen=select_search.best_estimator_; best_k=int(select_search.best_params_["select__k"])
    names=np.array(FEATURES)[chosen.named_steps["select"].get_support()].tolist()
    ridge=GridSearchCV(pipeline(estimator=Ridge()),{"model__alpha":[.1,1.,10.,100.]},
                       scoring="neg_root_mean_squared_error",cv=cv,n_jobs=1,refit=True).fit(X_train,y_train)
    print(f"Selected k={best_k}; Ridge alpha={ridge.best_params_['model__alpha']}",flush=True)

    print("[3/7] Fitting predeclared benchmark models",flush=True)
    models={
        "Mean_baseline":(DummyRegressor(),0),
        "Single_feature_OLS":(pipeline(SelectKBest(f_regression,k=1)),1),
        "SelectKBest14_OLS":(pipeline(SelectKBest(f_regression,k=14)),14),
        "RFE14_OLS":(pipeline(RFE(LinearRegression(),n_features_to_select=14,step=1)),14),
        "OLS_all20":(pipeline(),20),
        "OLS_selected":(chosen,best_k),
        "Ridge":(ridge.best_estimator_,20),
        "HistGB_raw":(HistGradientBoostingRegressor(max_iter=180,max_leaf_nodes=15,learning_rate=.08,
                         l2_regularization=1.,early_stopping=False,random_state=SEED),None),
        "HistGB_with_sum":(HistGradientBoostingRegressor(max_iter=180,max_leaf_nodes=15,learning_rate=.08,
                         l2_regularization=1.,early_stopping=False,random_state=SEED),None),
        "Sum_feature_OLS":(LinearRegression(),1),
    }
    rows=[]
    for name,(model,p) in models.items():
        if name=="HistGB_with_sum":
            train_values=X_train.assign(FeatureSum=X_train.sum(axis=1))
            test_values=X_test.assign(FeatureSum=X_test.sum(axis=1))
        elif name=="Sum_feature_OLS":
            train_values=X_train.sum(axis=1).to_numpy().reshape(-1,1)
            test_values=X_test.sum(axis=1).to_numpy().reshape(-1,1)
        else: train_values,test_values=X_train,X_test
        model.fit(train_values,y_train)
        train_pred=model.predict(train_values);test_pred=model.predict(test_values)
        cv_scores=-cross_val_score(clone(model),train_values,y_train,cv=cv,scoring="neg_root_mean_squared_error",n_jobs=1)
        rows.append({"model":name,"n_inputs":p,"train_RMSE":float(np.sqrt(mean_squared_error(y_train,train_pred))),
                     "CV_RMSE":float(cv_scores.mean()),"CV_SD":float(cv_scores.std()),**metrics(y_test,test_pred,p)})
        # Test results are reported together only after all settings were fixed.
        print(f"  Fitted {name}",flush=True)
    result=pd.DataFrame(rows);result.to_csv(output/"tables"/"model_metrics.csv",index=False)

    print("[4/7] OLS inference and independent calibration intervals",flush=True)
    X_trans=chosen[:-1].transform(X_train)
    fitted=sm.OLS(y_train.to_numpy(),sm.add_constant(X_trans,has_constant="add")).fit()
    test_trans=sm.add_constant(chosen[:-1].transform(X_test),has_constant="add")
    test_pred=chosen.predict(X_test)
    np.testing.assert_allclose(fitted.predict(test_trans),test_pred,atol=1e-10)
    sf=fitted.get_prediction(test_trans).summary_frame(alpha=.05)
    abs_cal=np.abs(y_cal.to_numpy()-chosen.predict(X_cal))
    rank=min(len(abs_cal),int(np.ceil((len(abs_cal)+1)*.95)))
    q=float(np.partition(abs_cal,rank-1)[rank-1])
    preds=pd.DataFrame({"id":sample.loc[test,"id"].to_numpy(),"actual":y_test.to_numpy(),"prediction":test_pred,
                         "mean_ci_lower":sf.mean_ci_lower.to_numpy(),"mean_ci_upper":sf.mean_ci_upper.to_numpy(),
                         "ols_pi_lower":sf.obs_ci_lower.to_numpy(),"ols_pi_upper":sf.obs_ci_upper.to_numpy(),
                         "conformal_lower":test_pred-q,"conformal_upper":test_pred+q})
    preds.to_csv(output/"tables"/"test_predictions.csv",index=False)
    intervals={"alpha":.05,"calibration_n":len(cal),"quantile_rank":rank,"conformal_q":q,
        "conformal_coverage":float(((preds.actual>=preds.conformal_lower)&(preds.actual<=preds.conformal_upper)).mean()),
        "conformal_mean_width":2*q,
        "ols_pi_coverage":float(((preds.actual>=preds.ols_pi_lower)&(preds.actual<=preds.ols_pi_upper)).mean()),
        "ols_pi_mean_width":float((preds.ols_pi_upper-preds.ols_pi_lower).mean()),
        "mean_ci_mean_width":float((preds.mean_ci_upper-preds.mean_ci_lower).mean()),
        "outside_01_predictions":int(((preds.prediction<0)|(preds.prediction>1)).sum())}
    save_json(output/"tables"/"interval_metrics.json",intervals)
    robust=fitted.get_robustcov_results(cov_type="HC3");ci=robust.conf_int()
    coef=pd.DataFrame({"feature":["const"]+names,"coefficient":fitted.params,"hc3_lower":ci[:,0],"hc3_upper":ci[:,1],"hc3_p":robust.pvalues})
    coef.to_csv(output/"tables"/"ols_coefficients.csv",index=False)
    original_coefs=chosen.named_steps["model"].coef_/chosen.named_steps["scale"].scale_[chosen.named_steps["select"].get_support()]
    original_intercept=float(chosen.named_steps["model"].intercept_-np.dot(original_coefs,chosen.named_steps["scale"].mean_[chosen.named_steps["select"].get_support()]))
    save_json(output/"tables"/"original_unit_equation.json",{"intercept":original_intercept,"coefficients":dict(zip(names,original_coefs.tolist()))})
    fitted_summary=str(fitted.summary());(output/"tables"/"ols_summary.txt").write_text(fitted_summary,encoding="utf-8")

    print("[5/7] Checking regression assumptions on proper training data",flush=True)
    bp=het_breuschpagan(fitted.resid,fitted.model.exog)
    jb=jarque_bera(fitted.resid)
    reset=linear_reset(fitted,power=3,test_type="fitted",use_f=True)
    vif=pd.DataFrame({"feature":names,"VIF":[variance_inflation_factor(fitted.model.exog,i+1) for i in range(len(names))]})
    vif.to_csv(output/"tables"/"vif.csv",index=False)
    diagnostics={"reset_F":float(reset.fvalue),"reset_p":float(reset.pvalue),
        "breusch_pagan_LM":float(bp[0]),"breusch_pagan_p":float(bp[1]),
        "jarque_bera":float(jb[0]),"jarque_bera_p":float(jb[1]),"residual_skew":float(jb[2]),"residual_kurtosis":float(jb[3]),
        "durbin_watson_arbitrary_order":float(durbin_watson(fitted.resid)),"max_vif":float(vif.VIF.max()),
        "independence_note":"No timestamps or spatial groups; independence cannot be established with this dataset. DW is descriptive in an arbitrary row order."}
    save_json(output/"tables"/"diagnostics.json",diagnostics)
    scores=chosen.named_steps["select"].scores_
    ranking=pd.DataFrame({"feature":FEATURES,"f_score":scores,"selected":chosen.named_steps["select"].get_support(),
                          "kbest14_selected":models["SelectKBest14_OLS"][0].named_steps["select"].get_support(),
                          "rfe14_selected":models["RFE14_OLS"][0].named_steps["select"].get_support()})
    ranking.sort_values("f_score",ascending=False).to_csv(output/"tables"/"feature_ranking.csv",index=False)

    # The original file is audited separately; it is never mixed into modeling.
    original_path=ROOT/"data"/"flood.csv"
    audit={}
    if original_path.exists():
        original=pd.read_csv(original_path)
        audit={"n":len(original),"max_abs_error_target_minus_sum_over_200":float(np.abs(original[FEATURES].sum(axis=1)/200-original[TARGET]).max())}
    metadata={"dataset_url":"https://www.kaggle.com/datasets/naiyakhalid/flood-prediction-dataset",
        "competition_url":"https://www.kaggle.com/competitions/playground-series-s4e5/data",
        "retrieved_date":"2026-10-20","dataset_version":2,"source_file":"data/train.csv",
        "source_sha256":hashlib.sha256(Path(data).read_bytes()).hexdigest(),"source_rows":len(raw),
        "raw_columns":list(raw.columns),"input_features":FEATURES,"excluded_identifier":"id",
        "sampling":"pandas.DataFrame.sample(n=50000, random_state=42), before splitting",
        "sample_rows":len(sample),"proper_train_rows":len(proper),"calibration_rows":len(cal),"test_rows":len(test),
        "sample_missing_cells":int(sample.isna().sum().sum()),"sample_duplicate_rows_excluding_id":int(sample[FEATURES+[TARGET]].duplicated().sum()),
        "seed":SEED,"selected_k":best_k,"selected_features":names,"ridge_alpha":ridge.best_params_["model__alpha"],
        "sample_target_min":float(y.min()),"sample_target_max":float(y.max()),
        "original_file_audit":audit,"versions":{"python":os.sys.version.split()[0],"numpy":np.__version__,"pandas":pd.__version__,
            "scikit-learn":sklearn.__version__,"scipy":scipy.__version__,"statsmodels":statsmodels.__version__,"matplotlib":matplotlib.__version__},
        "cv_note":"For selected OLS and tuned Ridge, displayed CV is conditional on the selected setting; it is not nested-CV generalization performance. The untouched holdout is the final performance estimate."}
    save_json(output/"run_metadata.json",metadata)
    save_json(output/"models"/"model_card.json",{"selected_features":names,"prediction_interval":"95% split conformal",**intervals,
        "scope":"Educational synthetic-score prediction; not a calibrated estimate of real flood occurrence.","not_submitted_to_kaggle":True})
    joblib.dump({"pipeline":chosen,"ols":fitted,"conformal_q":q,"training_bounds":{"min":X_train.min(),"max":X_train.max()},"features":FEATURES},output/"models"/"ols_bundle.joblib")
    X_test.head(5).to_csv(ROOT/"data"/"new_samples.csv",index=False)
    print("[6/7] Exporting labeled figures",flush=True)
    make_figures(output/"figures",X_train,y_train,cvtab,result,preds,fitted,coef)
    print("[7/7] Completed; held-out test results follow",flush=True)
    print(result[["model","RMSE","MAE","R2"]].to_string(index=False))
    print(json.dumps(intervals,indent=2))
    return {"metadata":metadata,"metrics":result,"intervals":intervals,"diagnostics":diagnostics}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data",type=Path,default=ROOT/"data"/"train.csv")
    parser.add_argument("--output",type=Path,default=ROOT/"output")
    parser.add_argument("--predict",type=Path,help="CSV with the 20 original predictor columns")
    args=parser.parse_args()
    with threadpool_limits(limits=2):
        if args.predict: predict_new(args)
        else: run_analysis(args.data,args.output)


if __name__=="__main__":
    main()
