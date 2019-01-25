def page_classifier(url):
    
    import sys
    import os
    import re
    import requests
    import math
    from bs4 import BeautifulSoup
    from bs4 import Comment
    from bs4 import Tag
    import nltk
    from nltk import word_tokenize
    from nltk.tokenize import sent_tokenize
    from nltk.stem import WordNetLemmatizer
    from nltk.corpus import wordnet
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.tokenize import RegexpTokenizer
    from collections import defaultdict
    from collections import Counter
    
    ##############################################################################################
    ##############################################################################################
    
    # URL Error handling
    def urlCheck(url, cookie=None):
        """
        input:  url (string)
        output: status of given url (string), response (requests.models.Response)
        """
        try:
            sess = requests.session
            header = {'cookie':cookie}
            user_agent = {'User-agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=user_agent)
            r.raise_for_status()
            return "Pass", r
        except requests.exceptions.HTTPError as errh:
            return "Http Error:", errh
        except requests.exceptions.ConnectionError as errc:
            return "Connection Error:", errc
        except requests.exceptions.Timeout as errt:
            return "Timeout Error:", errt
        except requests.exceptions.RequestException as err:
            return "Error:", err

    # Remove stopwords and punctuations in a given text, return tokenized object
    def preprocess(text):
        """
        input:  text (string)
        output: tokenized text (list)
        """
        text = text.lower()
        tokenizer = RegexpTokenizer(r'\w+')
        tokens = tokenizer.tokenize(text)
        lemmatizer = WordNetLemmatizer()
        tokens = [lemmatizer.lemmatize(token) for token in tokens]
        tokens = [str(w) for w in tokens if not w in stopwords.words('english') and len(w) >= 3]
        return tokens
    
    # Select keywords by POS tags, according to a priority list (select nouns and verbs first)
    def select_by_tags(wordList, k=5):
        """
        input:  list of words (list), number of words to be selected (int, optional)
        output: list of selected words (list)
        """
        if len(wordList) < k:
            return wordList
        ans = []
        tagDict = defaultdict(list)
        for word, tag in nltk.pos_tag(wordList):
            tagDict[tag].append(word)
        tags = ['NNP','NNPS','NN','NNS','VB','VBD','VBN','VBP','VBZ','VBG']
        while len(ans) < k:
            for tag in tags:
                ans += tagDict[tag]
        return ans
    
    # Retrive text of a bs4 element's children, treat each child's text as a document, transform unicode to string, remove elements with spaces only
    def element_to_documents(paragraphs):
        """
        input:  bs4 element (bs4.element.Tag)
        output: list of document/text (list)
        """
        documents = []
        for para in paragraphs.find_all(True):
            if len(para.text.strip()) > 0:
                documents.append(para.text.strip().encode('ascii','ignore'))
        return documents
    
    # Return k words with the highest scores
    def find_top_k(dictionary, k=5):
        """
        input:  dictionary of words and scores (dictionary: (key (word:string), value(score:float))), number of words to be selected (int, optional)
        output: list of selected words (list)
        """
        wordList = []
        for word, score in dictionary.iteritems():
            wordList.append([word, score])
        sortedList = sorted(wordList, key=lambda k:k[1], reverse=True)
        topK = []
        for j in range(min(k, len(sortedList))):
            topK.append(sortedList[j][0]) 
        return topK
    
    # Remove element according to element's text
    def strip_element(soup):
        """
        input:  BeautifulSoup object of a given web page (bs4.BeautifulSoup)
        output: cleaned/trimmed BeautifulSoup object (bs4.BeautifulSoup)
        """
        for element in soup.find_all(True):
            element.attrs = {}    
            if len(element.renderContents().strip()) == 0 :
                element.extract()
        return soup
    
    # Clear a given html according to tags and texts of elements
    def clear_html(soup): 
        """
        input:  BeautifulSoup object of a given web page (bs4.BeautifulSoup)
        output: cleaned/trimmed BeautifulSoup object (bs4.BeautifulSoup)
        """
        # delete comments
        def delete_comments(soup):
            comments = soup.find_all(text=lambda text:isinstance(text, Comment))
            [comment.extract() for comment in comments]
        delete_comments(soup)

        # convert tag to text
        def delete_syntax(soup, tagList):
            for tag in tagList:
                map(lambda x: x.replaceWith(x.text.strip()), soup.find_all(tag))
        delete_syntax_list = ["li", "em", "tt"]
        delete_syntax(soup, delete_syntax_list)

        # delete certain tags
        def delete_tags(soup, tagList):
            for tag in tagList:
                map(lambda x: x.extract(), soup.find_all(tag))
        delete_tags_list = ["code", "style", "script", "link", "head", "meta", "footer", "href"]
        delete_tags(soup, delete_tags_list)

        # delete tags with no text
        def delete_no_text(soup, tagList):
            for tag in tagList:
                for para in soup.find_all(tag):
                    if(len(para.renderContents().strip()) == 0):
                        para.extract()
        delete_no_text_list = ["td", "tr", "div"]
        delete_no_text(soup, delete_no_text_list)

        # delete tags with short text or few descendents
        def delete_short(soup, tagList):
            for tag, lenOfText, numOfDsc in tagList:
                for para in soup.find_all(tag):
                    if(len(para.text) < lenOfText and len(para) <= numOfDsc):
                        para.extract()
        delete_short_list = [["td", 50, 2], ["tr", 50, 2], ["div", 50, 2], ["table", 50, 2], ["p", 50, 2]]
        delete_short(soup, delete_short_list)

        # replace certain tags with 'p'
        def replace_tag(soup, tagList):
            for tag in tagList:
                for t in soup.find_all(tag):
                    t.name = "p"
                    t.attrs = {}
        replace_tag_list = ['blockquote', 'quote', 'div', 'span']
        replace_tag(soup, replace_tag_list)
        return soup

    # Arc90 Readability algorithm, used to retrive the main text content of a given web page
    def arc90_readability(r):
        """
        input:  response of an url (requests.models.Response)
        output: bs4 element with the highest score, also with the main text content in this algorithm (bs4.element.Tag)
        """
        # scorers 
        NEGATIVE = re.compile(".*comment.*|.*meta.*|.*footer.*|.*foot.*|.*cloud.*|.*head.*|.*link.*|.*review.*|.*hide.*|.*facebook.*|.*twitter.*|.*time.*|.*twitter.*")
        POSITIVE = re.compile(".*post.*|.*hentry.*|.*entry.*|.*content.*|.*text.*|.*body.*|.*description.*|.*article.*|.*paragraph.*|.*title.*|.*product.*|.*detail.*|.*story.*|.*text.*")
        pattern = re.compile("<br */? *>[ rn]*<br */? *>")

        soup = BeautifulSoup(re.sub(pattern, "</p><p>", r.text))
        soup = clear_html(soup)
        topElement = None
        parentsDict = defaultdict(int)

        for paragraph in soup.find_all('p'): 
            parent = paragraph.parent
            
            # score calculator, based on key words and length of text
            if parent not in parentsDict:
                parentsDict[parent] = 0            
                if (parent.has_attr("class")):
                    if (NEGATIVE.match(str(parent["class"]))):
                        parentsDict[parent] -= 50
                    elif (POSITIVE.match(str(parent["class"]))):
                        parentsDict[parent] += 50

                if (parent.has_attr("id")):
                    if (NEGATIVE.match(str(parent["id"]))):
                        parentsDict[parent] -= 50
                    elif (POSITIVE.match(str(parent["id"]))):
                        parentsDict[parent] += 50
            if (len( paragraph.renderContents() ) > 10):
                parentsDict[parent] += len(paragraph.renderContents())/100

        parentsList = []    
        for tag, score in parentsDict.iteritems():
            parentsList.append((tag, score))
        topElement = max(parentsList, key=lambda x: x[1])[0]
        stripElement = strip_element(topElement)

        return stripElement
    
    ##############################################################################################
    ######################          3 ways to retrive topic words        #########################
    ##############################################################################################
    
    # 1. Get topics from page's title, title is obtained by parsing HTML
    def title_topics(soup):
        headers = []
        for h in ['h1', 'h2']:
            headers += soup.find_all(h)
        if not headers:
            return []
        titleWords = preprocess(headers[0].get_text().strip().encode('ascii','ignore'))
        return select_by_tags(titleWords)

    # 2. Get topics according to frequency of words, main content is obtained using Arc90 Readability algorithm
    def word_freq(paragraphs, k=5):
        documents = element_to_documents(paragraphs)
        text = ''
        for doc in documents:
            text += doc

        wordDict = Counter(preprocess(text))
        return find_top_k(wordDict)

    # 3. Get topics according to TF-IDF score of words, main content is obtained using Arc90 Readability algorithm
    def tf_idf(paragraphs, k=5):
        documents = element_to_documents(paragraphs)
        size = len(documents)

        tf = []
        idf = defaultdict(float)
        tfidf = defaultdict(float)

        # generate tf dictionaries for each document
        for idx in range(size):
            doc = documents[idx]
            tokens = preprocess(doc)
            tf.append(Counter(tokens))

        # calculate tf-idf score for each word
        for idx in range(size):
            dictionary = tf[idx]
            for word, freq in dictionary.iteritems():
                # prune to save time
                if word in tfidf:
                    continue
                else:
                    if word in idf:
                        tfidf[word] = tf[idx][word] * idf[word]
                    else:
                        idf[word] = math.log(size / len([i for i in range(size) if tf[i][word] > 0]))
                        tfidf[word] = tf[idx][word] * idf[word]
        # sort words by score
        return find_top_k(tfidf)
    
    ##############################################################################################
    ##############################################################################################
    
    status, r = urlCheck(url)
    if status != 'Pass':
        print status, r
        #return []
    soup = BeautifulSoup(r.text,'lxml')
    topics = []
    
    # combine 3 ways to get final answer
    topics += title_topics(soup)
    paragraphs = arc90_readability(r)
    topics += word_freq(paragraphs)
    topics += tf_idf(paragraphs)

    return list(set(topics))


    ##############################################################################################
    ##############################################################################################









if __name__ == "__main__":
    
    testUrls = ['https://www.cnn.com/2013/06/10/politics/edward-snowden-profile/', \
                'https://www.rei.com/blog/camp/how-to-introduce-your-indoorsy-friend-to-the-outdoors', \
                'https://www.amazon.com/Cuisinart-CPT-122-Compact-2-SliceToaster/dp/B009GQ034C/ref=sr_1_1?s=kitchen&ie=UTF8&qid=1431620315&sr=1-1&keywords=toaster'\
               ]
    
    for i in range(len(testUrls)):
        url = testUrls[i]
        print "- Test ", str(i+1)
        print "Url: ", url
        print "Topics: ", page_classifier(url), '\n'


    # Call the function as following:
    # page_classifier(url)


