import requests
from bs4 import BeautifulSoup
from pprint import pprint
url ='http://127.0.0.1:5000'
#response = requests.get(url)
#response.raise_for_status()


session = requests.Session() # session -- объект сессии
response = session.get(url) # весь html код воспринимается как string
#print(response.text) # возвращает весь html код в виде string
dom = BeautifulSoup(response.text, 'html.parser') # преобразует, полученный html текст в стуктуру DOM.После такого преобразования\\
#print(dom)                                               # можно с помощью методов обращаться к элеметам структуры DOM- тегам
result = dom.find("a") # метод find ищет первый встречный тег
#print(result)
#print(result.text)
#print(result.get('href')) # get позволяет получить значение по любому атрибуту
#print(result.parent) # свойство parent позволяет найти родителя у тега <a> -- это тег <p>
tag_a = dom.find("a")
#print(result.parent.parent) #  можно вызывать свойство parant несколько раз. В данном случае мы получим деда тег <a> -- <div>
div = result.parent.parent
children_div = div.children
#pprint(list(children_div)) # children_div считает детей тега <div>  и в том числе "заахватывает всякий мусор типа "/n"
#pprint(list(div.findChildren())) #потомков тоже показывает, но и всех вложенных
#pprint(list(div.findChildren(recursive=False)))# Если хотите получить всех потомков на одном уровне, поставьте аргумент//
                                                # recursive=False

tag_p = dom.find('p', {'class':'paragraph'}) # поиск тега по имени класса.
#print(tag_p)
tag_p = dom.find('p', {'id':'clickable'}) #поиск тега по имени id.
#print(tag_p)
tags_p = dom.find_all("p")
#pprint(tags_p)
#tags_p = dom.find_all("p", {'class':'paragraph'})
#pprint(tags_p)
tags = dom.find('p', {'class':['red','paragraph',]})
#print(tags)


# поиск по Selectors
tags_p = dom.select('p.red.paragraph')
print(tags_p)
