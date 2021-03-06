#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan 27 23:33:28 2018

@author: jmkovachi
"""

import numpy
import math
from read_movie_reviews import read_Movies as movie_reader

class MaxEnt:
    
    """
    feature_set is a list of all features in training set
    document_set is a list of all documents
    class_set is a list of all classes
    """
    @staticmethod
    def train(feature_set, document_set, class_set):
        
        normalizing_param = {}
        
        expected_prior = {}
        
        for feature in feature_set:
            normalizing_param[feature] = 1    
        
        normalizing_param["**k+1**"] = 1
        
        count = 0
           
        c = 0
        for feature in feature_set:
            count = 0
            c += 1
            for doc in document_set: 
                if feature in doc[0]:
                    count += 1
            expected_prior[feature] = count / len(document_set)
            
        iter_count = 0
        
        flag = True
        while(flag):
            
            
            # calculate the max Constant value
            max_C = 0
            pos_features = 0
            neg_features = 0
            for doc in document_set:
                for cl in class_set:
                    tmp = 0
                    for feature in feature_set:
                        if feature in doc[0] and cl == doc[1]:
                            if cl == 'positive':
                                pos_features += 1
                            elif cl == 'negative':
                                neg_features += 1
                            tmp += 1
                    if tmp > max_C:
                        max_C = tmp
                    
            
            
            for i in range(0, len(document_set)):
                
                for key, cl in document_set[i][2].items():
                    document_set[i][2][key] = 1
                    feature_weight = 0
                    count = 0
                    for feature in feature_set:
                        
                        feature_weight = 1 if feature in doc[0] and key == document_set[i][1] else 0
                        document_set[i][2][key] *= (normalizing_param[feature] ** feature_weight)

                             
                    tmp_sum = pos_features if cl == 'positive' else neg_features
                    if key == '**k+1**':
                        document_set[i][2][key] *= max_C - tmp_sum
                        
                    # calculate normalizing constant
                    document_set[i][2][key] /= MaxEnt.calculate_Norm_Constant(class_set, feature_set, document_set[i], normalizing_param)
            iter_count += 1
            print(iter_count)
            for feature in feature_set:
                if (expected_prior[feature] - MaxEnt.calculate_Expected(document_set, feature) < .05 and expected_prior[feature] - MaxEnt.calculate_Expected(document_set, feature) > 0):
                    flag = False
                    break
                normalizing_param[feature] = normalizing_param[feature] * ((expected_prior[feature] / MaxEnt.calculate_Expected(document_set, feature))**(1/max_C))
            
        return normalizing_param
                            
    @staticmethod
    def count(feature, doc_set, cl):
        count = 0
        for index in range(0,doc_set):
            count = count + 1 if doc_set[index][1] == cl and feature in doc_set[index] else count
                
        return count
    
    @staticmethod
    def calculate_Norm_Constant(class_set, feature_set, document, normalizing_param):
        Z = 0
        for cl in class_set:
            tmp = 1
            for feature in feature_set:
                feature_weight = 0
                if feature in document[0] and document[1] == cl:
                    feature_weight = 1
                tmp *= (normalizing_param[feature] ** feature_weight)
            Z += tmp
               
        return Z
  
    @staticmethod
    def calculate_Expected(document_set, feature):
        sumVal = 0
        classes = ['positive', 'negative']
        for cl in classes:
            for index in range(0,len(document_set)):
                sumVal += document_set[index][2][cl] * (1 if feature in document_set[index][0] and document_set[index][1] == cl else 0)
        return sumVal
    
    @staticmethod
    def test(normalizing_param, feature_list, cl, document):
        prob = 1
        for feature in feature_list:
            prob *= normalizing_param[feature] ** (1 if feature in document[0] and document[1] == cl else 0)
        return prob / MaxEnt.calculate_Norm_Constant(['positive', 'negative'], feature_list, document, normalizing_param)
            
                
                    
                    
feature_list, document_list = movie_reader.read_dir('/home/jmkovachi/sent-classifier/movie_reviews/txt_sentoken/')
print(feature_list)
normalizing_param = MaxEnt.train(feature_list, document_list, ('positive', 'negative'))


            
