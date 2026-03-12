# ISBN Renamer

Ferramenta CLI para processar bibliotecas de livros digitais (PDF, EPUB, MOBI): extrai o ISBN de cada arquivo, busca título e autor nas APIs da CBL e Google Books, e renomeia os arquivos automaticamente no formato `Título - Autor.ext`.

## Dependências do sistema

Antes de instalar, certifique-se de ter estes programas instalados:

```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr poppler-utils exiftool

# macOS
brew install tesseract poppler exiftool
```

## Instalação

```bash
# Clone o repositório
git clone <url-do-repo>
cd isbn-renamer

# Crie o ambiente e instale as dependências com uv
uv sync
```

## Uso

```bash
uv run isbn.py
```

Uma janela de seleção de pasta será aberta. Escolha a pasta com seus livros. O script irá:

1. Encontrar todos os arquivos `.pdf`, `.epub` e `.mobi`
2. Extrair o ISBN via texto ou OCR (600 DPI para PDFs)
3. Buscar metadados na **CBL** (Câmara Brasileira do Livro) e **Google Books**
4. Gravar os metadados no arquivo e renomear para `Título - Autor.ext`

## Fluxo de extração

```
Arquivo PDF  →  pdfminer (texto)  →  ISBN encontrado?
                       ↓ não
             OCR 600 DPI (pytesseract)  →  ISBN encontrado?
                       ↓ não
             "ISBN não localizado nas 10 páginas"

Arquivo EPUB →  ebooklib + BeautifulSoup  →  ISBN encontrado?
```

## Desenvolvimento

```bash
# Instala dependências de dev
uv sync --extra dev

# Linting
uv run ruff check .

# Testes
uv run pytest
```
