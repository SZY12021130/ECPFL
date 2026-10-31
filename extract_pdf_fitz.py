import fitz, os
pdf_path = r'E:\GithubProjects\paperlist\25-FedFetch.pdf'
doc = fitz.open(pdf_path)
out = r'E:\GithubProjects\paperlist\25-FedFetch_fitz.txt'
pages = []
for i in range(len(doc)):
    page = doc.load_page(i)
    text = page.get_text()
    pages.append(f'--- Page {i+1} ---\n{text}\n')
with open(out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(pages))
print('done', len(doc), 'pages')
