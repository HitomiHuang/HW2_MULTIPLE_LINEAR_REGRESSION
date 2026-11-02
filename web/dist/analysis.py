"""Shared CPython/Pyodide engine. Training-only CV, independent calibration/test."""
from io import StringIO
import json
import math
import warnings
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 42

class FractionalSelect(TransformerMixin, BaseEstimator):
    """Fractional k handles category counts changing across training CV folds."""
    def __init__(self, fraction=1.):
        self.fraction = fraction
    def fit(self, X, y):
        k = max(1,min(X.shape[1],int(math.ceil(X.shape[1]*self.fraction))))
        self.selector_ = SelectKBest(f_regression,k=k).fit(X,y)
        return self
    def transform(self, X):
        return self.selector_.transform(X)
    def get_support(self):
        return self.selector_.get_support()

def read_csv(text):
    frame = pd.read_csv(StringIO(text), sep=None, engine='python')
    frame.columns = frame.columns.astype(str).str.strip()
    if frame.columns.duplicated().any():
        raise ValueError('CSV 有重複的欄位名稱，請先修正。')
    if len(frame.columns) < 2 or len(frame) < 30:
        raise ValueError('CSV 至少需要 2 欄及 30 筆資料。')
    return frame

def inspect_csv(text):
    df = read_csv(text)
    numeric = [c for c in df if pd.to_numeric(df[c], errors='coerce').notna().mean() > .8]
    excluded = [c for c in df if c.lower() in {'id','index','date'} or c.startswith('Unnamed:')]
    return json.dumps({'rows':len(df),'columns':list(df),'numeric':numeric,'excluded':excluded,
      'preview':df.head(5).fillna('').astype(str).to_dict('records')},ensure_ascii=False)

def run_analysis(text, target, excluded=None, max_rows=4000, alpha=.05):
    df=read_csv(text)
    if target not in df:
        raise ValueError('找不到指定的 Target 欄位。')
    excluded=[c for c in (excluded or []) if c in df and c != target]
    raw_features=[c for c in df if c != target and c not in excluded]
    if not raw_features:
        raise ValueError('至少需要一個輸入特徵。')
    y_all=pd.to_numeric(df[target],errors='coerce').replace([np.inf,-np.inf],np.nan)
    valid=y_all.notna()
    removed_target=int((~valid).sum())
    X=df.loc[valid,raw_features].copy()
    y=y_all[valid]
    if len(y)<30 or y.nunique()<2:
        raise ValueError('Target 必須是數值且至少有 30 筆有效資料及兩種不同數值。')
    if len(raw_features)>100:
        raise ValueError('互動版最多支援 100 個原始特徵，請先排除多餘欄位。')
    if len(X)>max_rows:
        X=X.sample(n=int(max_rows),random_state=SEED)
        y=y.loc[X.index]
    row_ids=X.index.to_numpy()
    train_idx,test_idx=train_test_split(np.arange(len(y)),test_size=.2,random_state=SEED)
    cal_count=max(int(math.ceil(len(train_idx)*.25)),int(math.ceil(1/alpha))-1)
    train_idx,cal_idx=train_test_split(train_idx,test_size=cal_count,random_state=SEED)
    numeric,categorical,dropped,notices=[],[],[],[]
    for c in raw_features:
        col=X.iloc[train_idx][c]
        if col.notna().sum()==0:
            dropped.append(c)
        elif pd.api.types.is_numeric_dtype(col) or pd.to_numeric(col,errors='coerce').notna().sum()==col.notna().sum():
            X[c]=pd.to_numeric(X[c],errors='coerce').replace([np.inf,-np.inf],np.nan)
            if X.iloc[train_idx][c].notna().sum()==0:
                dropped.append(c)
            else:
                numeric.append(c)
        elif col.nunique()>40:
            dropped.append(c)
        else:
            categorical.append(c)
            X[c]=X[c].map(lambda v:str(v) if pd.notna(v) else np.nan)
    active=numeric+categorical
    if not active:
        raise ValueError('沒有可建模欄位，請選擇數值或低基數類別特徵。')
    if dropped:
        notices.append('依訓練集排除全空或超過 40 類的文字欄位：'+', '.join(dropped))
    if len(y)<200:
        notices.append('樣本少於 200，交叉驗證與覆蓋率可能較不穩定。')
    prep=ColumnTransformer([
      ('numeric',Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True)),('scale',StandardScaler())]),numeric),
      ('categorical',Pipeline([('impute',SimpleImputer(strategy='most_frequent',keep_empty_features=True)),
       ('onehot',OneHotEncoder(handle_unknown='ignore',drop='first',sparse_output=False))]),categorical)
    ],remainder='drop',verbose_feature_names_out=False)
    Xtrain,ytrain=X.iloc[train_idx],y.iloc[train_idx]
    Xcal,ycal=X.iloc[cal_idx],y.iloc[cal_idx]
    Xtest,ytest=X.iloc[test_idx],y.iloc[test_idx]
    dimension=prep.fit_transform(Xtrain).shape[1]
    if dimension<1 or dimension>300:
        raise ValueError('編碼後特徵數須介於 1 與 300，請減少類別或欄位。')
    candidates=sorted(set([1/max(1,dimension),.5,.75,1.]))
    cv=KFold(n_splits=5,shuffle=True,random_state=SEED)
    selection=[]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        for fraction in candidates:
            pipe=Pipeline([('prepare',prep),('select',FractionalSelect(fraction)),('model',LinearRegression())])
            scores=-cross_val_score(pipe,Xtrain,ytrain,cv=cv,scoring='neg_root_mean_squared_error',error_score='raise')
            selection.append({'fraction':fraction,'k':max(1,int(math.ceil(dimension*fraction))),
              'rmse':float(scores.mean()),'sd':float(scores.std(ddof=1))})
        best=min(selection,key=lambda s:s['rmse'])
        final=Pipeline([('prepare',prep),('select',FractionalSelect(best['fraction'])),('model',LinearRegression())]).fit(Xtrain,ytrain)
        full=Pipeline([('prepare',prep),('model',LinearRegression())]).fit(Xtrain,ytrain)
    prediction=final.predict(Xtest)
    residuals_cal=np.abs(ycal.to_numpy()-final.predict(Xcal))
    rank=int(math.ceil((len(cal_idx)+1)*(1-alpha)))
    if rank>len(cal_idx):
        raise ValueError('校準資料不足以建立所選覆蓋率，請增加資料筆數。')
    q=float(np.sort(residuals_cal)[rank-1])
    lower,upper=prediction-q,prediction+q
    coverage=float(np.mean((ytest.to_numpy()>=lower)&(ytest.to_numpy()<=upper)))
    names=final.named_steps['prepare'].get_feature_names_out()
    selected_names=names[final.named_steps['select'].get_support()].tolist()
    p=len(selected_names)
    def metric(name,pred,count):
        r2=float(r2_score(ytest,pred))
        return {'model':name,'features':count,'mae':float(mean_absolute_error(ytest,pred)),
          'mse':float(mean_squared_error(ytest,pred)),'rmse':float(np.sqrt(mean_squared_error(ytest,pred))),
          'r2':r2,'adjusted_r2':1-(1-r2)*(len(ytest)-1)/(len(ytest)-count-1) if len(ytest)>count+1 else None}
    metrics=[metric('平均值基線',np.repeat(ytrain.mean(),len(ytest)),0),
      metric('全特徵 LinearRegression',full.predict(Xtest),dimension),
      metric('特徵選擇 LinearRegression',prediction,p)]
    rows=[{'row':int(row_ids[test_idx[i]])+2,'actual':float(ytest.iloc[i]),'prediction':float(prediction[i]),
      'lower':float(lower[i]),'upper':float(upper[i]),'residual':float(ytest.iloc[i]-prediction[i])} for i in range(len(ytest))]
    coefficients=sorted([{'feature':name,'coefficient':float(v)} for name,v in zip(selected_names,final.named_steps['model'].coef_)],key=lambda c:abs(c['coefficient']),reverse=True)
    fitted_train=final.predict(Xtrain)
    residual_train=ytrain.to_numpy()-fitted_train
    jb=stats.jarque_bera(residual_train)
    transformed=final.named_steps['select'].transform(final.named_steps['prepare'].transform(Xtrain))
    design=np.column_stack([np.ones(len(transformed)),transformed])
    rank_design=int(np.linalg.matrix_rank(design))
    df_resid=len(ytrain)-rank_design
    test_design=np.column_stack([np.ones(len(ytest)),final.named_steps['select'].transform(final.named_steps['prepare'].transform(Xtest))])
    pinv=np.linalg.pinv(design)
    leverage=np.sum((test_design@pinv)**2,axis=1)
    sigma2=float(np.sum(residual_train**2)/df_resid) if df_resid>0 else None
    if sigma2 is not None:
        tcrit=float(stats.t.ppf(1-alpha/2,df_resid))
        ci=tcrit*np.sqrt(sigma2*leverage)
        pi=tcrit*np.sqrt(sigma2*(1+leverage))
        for i,row in enumerate(rows):
            row.update({'mean_ci_lower':float(prediction[i]-ci[i]),'mean_ci_upper':float(prediction[i]+ci[i]),
              'ols_pi_lower':float(prediction[i]-pi[i]),'ols_pi_upper':float(prediction[i]+pi[i])})
    condition=float(np.linalg.cond(design))
    diagnostic={'jarque_bera_p':float(jb.pvalue),'design_rank':rank_design,'design_columns':p+1,
      'residual_df':df_resid,'condition_number':condition if np.isfinite(condition) else None}
    if rank_design<p+1:
        notices.append('設計矩陣秩不足（存在共線性），採 SVD 最小範數解；個別係數無唯一解。OLS 區間僅供參考，主要採校準預測區間。')
    if sigma2 is not None and np.sqrt(sigma2)<max(1,abs(float(ytrain.mean())))*1e-10:
        notices.append('目標與特徵近乎完全線性，請檢查目標洩漏或人工公式。')
    qq=stats.probplot(residual_train,dist='norm',fit=False)
    stride=max(1,len(ytrain)//500)
    return json.dumps({'target':target,'source_rows':len(df),'sample_rows':len(y),'seed':SEED,
      'removed_target':removed_target,'excluded':excluded,'dropped':dropped,'original_features':len(raw_features),
      'active_features':len(active),'encoded_features':dimension,'assignment_eligible':13<len(raw_features)<40,
      'selected_features':selected_names,'split':{'train':len(train_idx),'calibration':len(cal_idx),'test':len(test_idx)},
      'selection':selection,'metrics':metrics,'interval':{'level':1-alpha,'q':q,'rank':rank,'coverage':coverage,'width':2*q},
      'coefficients':coefficients,'intercept':float(final.named_steps['model'].intercept_),'predictions':rows,
      'diagnostics':diagnostic,'notices':notices,
      'training_residuals':[{'fitted':float(a),'residual':float(b)} for a,b in zip(fitted_train[::stride],residual_train[::stride])],
      'qq':[{'theoretical':float(a),'observed':float(b)} for a,b in zip(qq[0][::stride],qq[1][::stride])],
      'provenance':{'engine':'scikit-learn LinearRegression','selection':'5-fold training CV + F ranking',
        'interval':'finite-sample split-conformal, independent calibration','version':1},
      'split_rows':{'train':[int(row_ids[i])+2 for i in train_idx],'calibration':[int(row_ids[i])+2 for i in cal_idx],'test':[int(row_ids[i])+2 for i in test_idx]}},ensure_ascii=False,allow_nan=False)
