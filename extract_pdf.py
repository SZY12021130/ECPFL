import PyPDF2
pdf_path = r'E:\GithubProjects\paperlist\25-FedFetch.pdf'
txt_path = r'E:\GithubProjects\paperlist\25-FedFetch.txt'
reader = PyPDF2.PdfReader(pdf_path)
texts = []
for i, page in enumerate(reader.pages):
    try:
        t = page.extract_text()
    except Exception as e:
        t = ''
    texts.append(f'--- Page {i+1} ---\n{t}\n')
with open(txt_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(texts))
print(f'Extracted {len(reader.pages)} pages to {txt_path}')
