"""
通达信公式函数库 - 序列原语（0级核心函数 + 1级应用函数）

来源：通达信公式函数的 Python/pandas 实现
内容：REF/HHV/LLV/MA/EMA/SMA/DMA/CROSS/BARSLAST 等 40 余个底层序列函数

约定：
- 输入 S 为 numpy 数组或 pandas Series，输出为 numpy 数组
- 滚动窗口类函数（MA/HHV/LLV/STD 等）前 N-1 个值为 NaN（通达信标准行为）
- EMA/SMA 等指数平滑类函数从首个有效值开始递推
"""

import pandas as pd
import numpy as np
def RD(N,D=3):   
    #四舍五入取3位小数 
    return np.round(N,D)        
def RET(S,N=1):  
    #返回序列倒数第N个值,默认返回最后一个
    return np.array(S)[-N]      
def ABS(S):  
    #返回N的绝对值    
    return np.abs(S)            
def MAX(S1,S2): 
    #序列max 
    return np.maximum(S1,S2)    
def MIN(S1,S2):  
     #序列min
    return np.minimum(S1,S2)   
def IF(S,A,B): 
    #序列布尔判断 return=A  if S==True  else  B  
    return np.where(S,A,B)      
def AND(S1,S2):
    #and
    return np.logical_and(S1,S2)
def OR(S1,S2):
    #or
    return np.logical_or(S1,S2)
def RANGE(A,B,C):
    '''
    期间函数
    B<=A<=C
    '''
    df=pd.DataFrame()
    df['select']=A.tolist()
    df['select']=df['select'].apply(lambda x: True if (x>=B and x<=C) else False)
    return df['select']

def REF(S, N=1):          #对序列整体下移动N,返回序列(shift后会产生NAN)    
    return pd.Series(S).shift(N).values  

def DIFF(S, N=1):         #前一个值减后一个值,前面会产生nan 
    return pd.Series(S).diff(N).values     #np.diff(S)直接删除nan，会少一行

def STD(S,N):             #求序列的N日标准差，返回序列    
    return  pd.Series(S).rolling(N).std(ddof=0).values     

def SUM(S, N):            #对序列求N天累计和，返回序列    N=0对序列所有依次求和         
    return pd.Series(S).rolling(N).sum().values if N>0 else pd.Series(S).cumsum().values  

def CONST(S):             #返回序列S最后的值组成常量序列
    return np.full(len(S),S[-1])
  
def HHV(S,N):             #HHV(C, 5) 最近5天收盘最高价        
    return pd.Series(S).rolling(N).max().values     

def LLV(S,N):             #LLV(C, 5) 最近5天收盘最低价     
    return pd.Series(S).rolling(N).min().values    
    
def HHVBARS(S,N):         #求N周期内S最高值到当前周期数, 返回序列
    return pd.Series(S).rolling(N).apply(lambda x: np.argmax(x[::-1]),raw=True).values 

def LLVBARS(S,N):         #求N周期内S最低值到当前周期数, 返回序列
    return pd.Series(S).rolling(N).apply(lambda x: np.argmin(x[::-1]),raw=True).values    
  
def MA(S,N):              #求序列的N日简单移动平均值，返回序列                    
    return pd.Series(S).rolling(N).mean().values  
  
def EMA(S,N):             #指数移动平均,为了精度 S>4*N  EMA至少需要120周期     alpha=2/(span+1)    
    return pd.Series(S).ewm(span=N, adjust=False).mean().values     

def SMA(S, N, M=1):       #中国式的SMA,至少需要120周期才精确 (雪球180周期)    alpha=1/(1+com)    
    return pd.Series(S).ewm(alpha=M/N,adjust=False).mean().values           #com=N-M/M

def DMA(S, A):            #求S的动态移动平均，A作平滑因子,必须 0<A<1  (此为核心函数，非指标）
    return pd.Series(S).ewm(alpha=A, adjust=True).mean().values

def WMA(S, N):            #通达信S序列的N日加权移动平均 Yn = (1*X1+2*X2+3*X3+...+n*Xn)/(1+2+3+...+Xn)
    return pd.Series(S).rolling(N).apply(lambda x:x[::-1].cumsum().sum()*2/N/(N+1),raw=True).values 
  
def AVEDEV(S, N):         #平均绝对偏差  (序列与其平均值的绝对差的平均值)   
    return pd.Series(S).rolling(N).apply(lambda x: (np.abs(x - x.mean())).mean()).values 

def SLOPE(S, N):          #返S序列N周期回线性回归斜率            
    return pd.Series(S).rolling(N).apply(lambda x: np.polyfit(range(N),x,deg=1)[0],raw=True).values

def FORCAST(S, N):        #返回S序列N周期回线性回归后的预测值， jqz1226改进成序列出    
    return pd.Series(S).rolling(N).apply(lambda x:np.polyval(np.polyfit(range(N),x,deg=1),N-1),raw=True).values  

def LAST(S, A, B):        #从前A日到前B日一直满足S_BOOL条件, 要求A>B & A>0 & B>=0 
    return np.array(pd.Series(S).rolling(A+1).apply(lambda x:np.all(x[::-1][B:]),raw=True),dtype=bool)
  
#------------------   1级：应用层函数(通过0级核心函数实现） ----------------------------------
def COUNT(S, N):                       # COUNT(CLOSE>O, N):  最近N天满足S_BOO的天数  True的天数
    return SUM(S,N)    

def EVERY(S, N):                       # EVERY(CLOSE>O, 5)   最近N天是否都是True
    return  IF(SUM(S,N)==N,True,False)                    
  
def EXIST(S, N):                       # EXIST(CLOSE>3010, N=5)  n日内是否存在一天大于3000点  
    return IF(SUM(S,N)>0,True,False)

def FILTER(S, N):                      # FILTER函数，S满足条件后，将其后N周期内的数据置为0, FILTER(C==H,5)
    for i in range(len(S)): S[i+1:i+1+N]=0  if S[i] else S[i+1:i+1+N]        
    return S                           # 例：FILTER(C==H,5) 涨停后，后5天不再发出信号 
  
def BARSLAST(S):                       #上一次条件成立到当前的周期, BARSLAST(C/REF(C,1)>=1.1) 上一次涨停到今天的天数 
    M=np.concatenate(([0],np.where(S,1,0)))  
    for i in range(1, len(M)):  M[i]=0 if M[i] else M[i-1]+1    
    return M[1:]                       

def BARSLASTCOUNT(S):                  # 统计连续满足S条件的周期数        by jqz1226
    rt = np.zeros(len(S)+1)            # BARSLASTCOUNT(CLOSE>OPEN)表示统计连续收阳的周期数
    for i in range(len(S)): rt[i+1]=rt[i]+1  if S[i] else rt[i+1]
    return rt[1:]  
  
def BARSSINCEN(S, N):                  # N周期内第一次S条件成立到现在的周期数,N为常量  by jqz1226
    return pd.Series(S).rolling(N).apply(lambda x:N-1-np.argmax(x) if np.argmax(x) or x[0] else 0,raw=True).fillna(0).values.astype(int)

  
def CROSS(S1, S2):                     #判断向上金叉穿越 CROSS(MA(C,5),MA(C,10))  判断向下死叉穿越 CROSS(MA(C,10),MA(C,5))   
    return np.concatenate(([False], np.logical_not((S1>S2)[:-1]) & (S1>S2)[1:]))    # 不使用0级函数,移植方便  by jqz1226
def CROSS_UP(S1, S2):                     #判断向上金叉穿越 CROSS(MA(C,5),MA(C,10))  判断向下死叉穿越 CROSS(MA(C,10),MA(C,5))   
    return np.concatenate(([False], np.logical_not((S1>S2)[:-1]) & (S1>S2)[1:]))    # 不使用0级函数,移植方便  by jqz1226
def CROSS_DOWN(S1, S2):                     
    return np.concatenate(([False], np.logical_not((S1<S2)[:-1]) & (S1<S2)[1:]))    # 不使用0级函数,移植方便  by jqz1226

def LONGCROSS(S1,S2,N):                #两条线维持一定周期后交叉,S1在N周期内都小于S2,本周期从S1下方向上穿过S2时返回1,否则返回0         
    return  np.array(np.logical_and(LAST(S1<S2,N,1),(S1>S2)),dtype=bool)            # N=1时等同于CROSS(S1, S2)
    
def VALUEWHEN(S, X):                   #当S条件成立时,取X的当前值,否则取VALUEWHEN的上个成立时的X值   by jqz1226
    return pd.Series(np.where(S,X,np.nan)).ffill().values  
