from sklearn.cluster import KMeans
from sklearn import metrics
from scipy.spatial.distance import cdist
import numpy as np
from kneed import KneeLocator

def get_distortions(data, k_max):
    distortions = []
    k_values_to_test = range(1, k_max)
    for k in k_values_to_test:
        tac = data['TAC'].to_numpy().reshape(-1, 1)
        kmeansModel = KMeans(n_clusters=k)
        kmeansModel.fit(tac)
        distortions.append(kmeansModel.inertia_)
    return distortions, k_values_to_test

def get_knee(distortions, k_values_to_test):
    kn = KneeLocator(k_values_to_test, distortions, curve='convex', direction='decreasing')
    return kn.knee

def label_clusters(data, optimal_k):
    tac = data['TAC'].to_numpy().reshape(-1, 1)
    kmeans = KMeans(n_clusters=optimal_k)
    prediction = kmeans.fit_predict(tac)
    data['cluster'] = prediction
    return data

def get_tac_clusters(data):
    distortions, k_values_to_test = get_distortions(data, 10)
    optimal_k = get_knee(distortions, k_values_to_test)
    data = label_clusters(data, optimal_k)
    return data