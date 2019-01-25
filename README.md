# Page Classifier


## Requirements

```python
re
requests
bs4
nltk
```

## Usage

```python
# url: a string of url
page_classifier(url)
```

## Description

3 methods were used to individually get a list of topics. A combination of the words is returned as the final result. 

**1. Get Topics from Title by Parsing HTML**

This method was inspired by the intuitive way people usually use to grasp a general idea of a certain web page: reading it's title. Whether it be the title of an article or the description of an Amazon product.

I used HTML parsing on the header tags to get the title. Then I trimmed the title from stopwords and punctuations, and lemmatized it. POS tagging was used to evaluate the importance of each word.

**2. Get Topics from Words Frequency**

Before implementing this method, a grabbing step was performed to get the main content (text here) of a given web page. I first pruned the HTML object by elements' tags and text, getting rid of certain elements like footers, comments, or elements with very few text. Then I used **Arc90's Readability algorithm** to find the element containing the main content. It basically developes a scoring system according to attribute names and length of text, and selects the element with the highest score as the one with main content.


The same preprocessing steps were applied to the main text (remove stopwords and punctuations, as well as lemmatization). Then I simply counted the appearance of each words and returned the ones with highest frequency.

**3. Get Topics using tf–idf**

The same grabbing step were used prior to this method to get the main content of a web page, as well as the preprocessing steps. The elements within the selected main content were treated as a collection of documents. Tf-idf scores were also calculated for each words accordingly. Here, I used a dictionary to store each word's score. By checking a word's appearance in the dictionary before processing it, a significant amount of time is saved. The words with the highest tf–idf score were returned.



## Future Thoughts
**- Parameters in Arc90's Readability Algorithm**

The scorer plays a major part in this algorithm. Testing more urls and tuning the parameters will probably improve the results.

**- Rapid Automatic Keyword Extraction (RAKE) Algorithm**

This method can be useful to determine key phrases in a text body instead of words.

**- TextRank**

TextRank can help identifying important sentences in a text body.




