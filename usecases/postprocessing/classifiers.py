import numpy as np
from numpy.linalg import svd, norm
import random
from fdsketch.utils.syntheticDataMaker import SyntheticDataMaker

''' update storing entire history '''
class GlobalUpdate:
    def __init__(self) -> None:
        self.Nt = []

    def append(self, y):
        self.Nt.append(y)

    # return updated set of first k-left singular values
    def get_reconstruction_basis(self):
        [_,_,Vt] = svd(self.Nt, full_matrices=False)
        return Vt

class AnomalyClassifier:

    def __init__(self, k, sketch=GlobalUpdate, init_model = False, **kwargs) -> None:
        #self.Utk = Uo        # matrix of top-k left-singular vectors
        self.k = k
        self.model = sketch(**kwargs)
        self.Utk = None
        self.UtkT = None

        # Initialize with synthetic data if requested
        if init_model:
            n = kwargs.get('n', 10)      # number of samples for the random initialization
            m = kwargs.get('m', 10)       # feature size
            signal_dimension = kwargs.get('k', 5)  # signal dimension

            self._init_model(n, m, signal_dimension)
                
    
    def _init_model(self, n, m, k):
        # Generate synthetic data to initialize the model with a subspace representation
        dataMaker = SyntheticDataMaker()
        dataMaker.initBeforeMake(
            m,
            signal_dimension=k,
            signal_to_noise_ratio=10.0
        )
        
        # Generate training data and fit the model
        train_data = dataMaker.makeMatrix(n)
        self.fit(train_data)
    
    
    '''
        Classify input vector y either as anomalous or non-anomalous
            y : input column vector
            th : classification threshold, anomaly when above. 
            Deafult values are 0, which means never update classifier. This is
            useful to get the score distribution of the training set, without 
            modifying the classifier. 
    '''
    def classify(self, y, th=0, eta=0):
        # normalize input vector
        norm_ = norm(y)
        yn = y/norm_ if norm_ else y
        # optimal least-squares solution
        xi = yn @ self.Utk 
        # get anomaly score (objective value at the solution)
        score_vec = yn - xi @ self.UtkT
        score = norm(score_vec)
        # update left-singular values (use only non-anomalous data)
        if score <= th or random.random() < eta:
            self.__update__(yn)        
        # binary classification
        return (score > th, score, score_vec)

    ''' Update model with new sample '''
    def __update__(self, yn):
        self.model.append(yn)
        Vt = self.model.get_reconstruction_basis()
        # take first k rows (store both for performance)
        self.Utk = Vt[:self.k, :].T
        self.UtkT = Vt[:self.k, :]

    ''' Derive initial reconstruction basis Uk from a set of non-anomalous samples '''
    def fit(self, Y): 
        # obtain initial matrix of singular values, expects numpy array
        for y in Y:
            #y = row.to_numpy()
            norm_ = norm(y)
            yn = y/norm_ if norm_ else y
            self.__update__(yn)

