from xlrd import open_workbook
import re
import nltk
import math
import pandas as pd
import numpy as np
from elasticsearch import Elasticsearch
from QuandlWrapper import QuandlWrapper
from QueryES import QueryES
from pymongo import MongoClient
from companies import Companies
from TestResults import TestResults
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()
es = Elasticsearch()
queryES = QueryES()
quandl = QuandlWrapper()
client = MongoClient("mongodb://127.0.0.1:27018")
db = client['primer']


def find_incident_orgs(title):
    orgs = []
    for company in Companies.companies:
        if company[2].lower() in title.lower():
            orgs.append(company)
    return orgs


class McDonald_Word_List:

    def __init__(self):
        self.pos_words = {}
        self.neg_words = {}
        self.getWB()
        self.pos_word_counts = {word:0 for word, val in self.pos_words.items()}
        self.intersection_pos = {word:0 for word, val in self.pos_words.items()}
        self.neg_word_counts = {word:0 for word, val in self.neg_words.items()}
        self.intersection_neg = {word:0 for word,val in self.neg_words.items()}
        self.pos_df = None
        self.neg_df = None
        
    def __str__(self):
        print("""Pos words: {0}
                 Neg words: {1}""".format(
                  len(self.pos_words),
                  len(self.neg_words)))

    def getWB(self):
        """
        Gets the McDonald workbook excel file and stores all of its values in 
        the pos_words and neg_words dictionary member variable of the McDonald_Word_List
        class.
        """
        FORMAT = ['Positive', 'Negative']
        values = ""

        wb = open_workbook('McDonaldDict.xlsx')
        print('Getting polarity lists...')
        values = []
        for s in wb.sheets():
            words = []
            for row in range(1, s.nrows):
                col_names = s.row(0)[1:]
                col_value = []
                word = s.cell(row, 0).value
                for name, col in zip(col_names, range(1,s.ncols)):
                    value = (s.cell(row,col).value)
                    if name.value == 'Positive' and int(value) > 0:
                        self.pos_words[word] = int(value)
                    elif name.value == 'Negative' and int(value) > 0:
                        self.neg_words[word] = int(value)
                    col_value.append((name.value, value))
                values.append(col_value)

    def num_words(self, sentences):
        l = 0
        pos_count = 0
        neg_count = 0
        for s in sentences:
            l += len(s)
            words = [lemmatizer.lemmatize(word) for word in nltk.word_tokenize(s)]
            for word in words:
                if word.upper() in self.pos_words:
                    pos_count += 1
                elif word.upper() in self.neg_words:
                    neg_count += 1
        return l, pos_count, neg_count

    def compute_lexicon_score(self):
        true_pos = 0
        true_neg = 0
        false_pos = 0
        false_neg = 0
        for article in db.articles.find():
            orgs = find_incident_orgs(article['title'])
            try:
                #print(orgs)
                if len(orgs) != 0:
                    count, num_pos, num_neg = self.num_words(nltk.sent_tokenize(article['text']))
                    result = quandl.classification_decision(article['text'], orgs[0], article['time_string'], num_pos, num_neg)
                    if result == 'true-pos':
                        true_pos += 1
                    elif result == 'false-pos':
                        false_pos += 1
                    elif result == 'true-neg':
                        true_neg += 1
                    elif result == 'false-neg':
                        false_neg += 1
            except Exception as e:
                print(e)

        return TestResults.compute_scores(true_pos, true_neg, false_pos, false_neg)
        

    def compute_calculations(self, articles):
        length = 0
        overall_pos = 0
        overall_neg = 0
        self.overall_org = 0
        intersection_pos = 0
        intersection_neg = 0

        self.pos_df = pd.DataFrame(0, index=[str(key) for (key,val) in self.pos_words.items()], columns=[])
        self.neg_df = pd.DataFrame(0, index=[str(key) for (key,val) in self.neg_words.items()], columns=[])

        no_true = 0
        no_lex_true = 0
        no_false = 0
        no_lex_false = 0
        for article in articles:
            article = article['_source']
            sentences = nltk.sent_tokenize(article['text'])
            orgs = find_incident_orgs(article['title'])
            try:
                if orgs == 'Nothing':
                    continue
                else:
                    count, num_pos, num_neg = self.num_words(nltk.sent_tokenize(article['text']))
                    result = quandl.classification_decision(article['text'], orgs, article['date'], num_pos, num_neg)
                    if result[0]:
                        no_true += 1
                    elif not result[0]:
                        no_false += 1
                    if result[1]:
                        no_lex_true += 1
                    elif not result[1]:
                        no_lex_false += 1
                    continue

            except Exception as e:
                print(e)
                continue
            tmpL, tmp_pos, tmp_neg = self.num_words(sentences)
            length += tmpL
            overall_pos += tmp_pos
            overall_neg += tmp_neg
            for sent in sentences:
                org_count = 0
                pos_count = 0
                neg_count = 0
                org_list = []
                chunks = [chunk for chunk in nltk.ne_chunk(nltk.pos_tag(nltk.word_tokenize(sent)))]
                for chunk in chunks:
                        if hasattr(chunk, 'label') and str(chunk.label()) == 'ORGANIZATION':
                            org_count += 1
                            self.overall_org += 1
                            org_list.append(str(chunk[0]).upper())
                            if str(chunk[0]).upper() not in self.pos_df.columns:
                                self.pos_df[str(chunk[0]).upper()] = np.zeros(len(self.pos_df.index))
                                self.neg_df[str(chunk[0]).upper()] = np.zeros(len(self.neg_df.index))
                            
                tmp_org_count = org_count
                for chunk in chunks:
                        if str(chunk[0]).upper() in self.pos_words:
                            tmp_org_list = org_list
                            
                            
                            while len(tmp_org_list) > 0:
                                pos_count += 1
                                self.pos_df.at[str(chunk[0]).upper(), tmp_org_list[0]] += 1
                                tmp_org_list.pop(0)
                                self.intersection_pos[str(chunk[0]).upper()] += 1
                            self.pos_word_counts[str(chunk[0]).upper()] += 1
                        elif str(chunk[0]).upper() in self.neg_words:
                            tmp_org_list = org_list  
                            while(len(tmp_org_list) > 0):
                                neg_count += 1
                                self.neg_df.at[str(chunk[0]).upper(), tmp_org_list[0]] += 1
                                tmp_org_list.pop(0)
                                self.intersection_neg[str(chunk[0]).upper()] += 1
                            self.neg_word_counts[str(chunk[0]).upper()] += 1
            intersection_pos += org_count if org_count < pos_count else pos_count
            intersection_neg += org_count if org_count < neg_count else neg_count
            
    
    def visualize(self):
        import matplotlib.pyplot as plt

        sorted_counts = sorted(self.pos_word_counts.items(), key=lambda kv: kv[1], reverse=True)
        print(sorted_counts)
        print(sorted_counts[50][0])
        print(self.intersection_pos[sorted_counts[50][0]])
        print(McDonald_Word_List.compute_PMI(sorted_counts[100][1], self.overall_org, self.intersection_pos[sorted_counts[100][0]], l))

        sorted_counts[0:50]

        plt.figure(figsize=(20, 3))  # width:20, height:3
        # save the names and their respective scores separately
        # reverse the tuples to go from most frequent to least frequent 
        plt.bar(range(len(sorted_counts[0:20])), [val[1] for val in sorted_counts[0:20]], align='edge', width=.3)
        plt.xticks(range(len(sorted_counts[0:20])), [val[0] for val in sorted_counts[:20]])
        plt.xticks(rotation=70)
        plt.show()


        PMIs = [McDonald_Word_List.compute_PMI(count[1], self.overall_org, self.intersection_pos[count[0]], l) for count in sorted_counts[0:20]]

        plt.figure(figsize=(20, 3))  # width:20, height:3
        # save the names and their respective scores separately
        # reverse the tuples to go from most frequent to least frequent 
        plt.bar(range(len(sorted_counts[0:20])), PMIs, align='edge', width=.3)
        plt.xticks(range(len(sorted_counts[0:20])), [val[0] for val in sorted_counts[:20]])
        plt.xticks(rotation=70)
        plt.show()


    @staticmethod
    def compute_PMI(class1, class2, int_c1c2, overall_count):
        return math.log((int_c1c2+1/overall_count)/((class1+1/overall_count)*(class2+1/overall_count)))
        # +1s added for smoothing










