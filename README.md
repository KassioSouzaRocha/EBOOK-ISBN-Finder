# ISBN Renamer

Ferramenta CLI para processar bibliotecas de livros digitais (PDF, EPUB, MOBI): extrai o ISBN de cada arquivo, busca título e autor nas APIs da CBL e Google Books, e renomeia os arquivos automaticamente no formato `Título - Autor.ext`.

## Dependências do sistema

### Linux / macOS

```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr poppler-utils exiftool

# macOS
brew install tesseract poppler exiftool
```

### Windows

Instale as três ferramentas abaixo e adicione-as ao **PATH** (ou deixe nos caminhos padrão — o script detecta automaticamente):

| Ferramenta | Download | Caminho padrão detectado |
|---|---|---|
| **Tesseract OCR** | [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) | `C:\Program Files\Tesseract-OCR\tesseract.exe` |
| **Poppler** | [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) | `C:\Program Files\poppler\Library\bin` |
| **ExifTool** | [exiftool.org](https://exiftool.org) | Adicionar ao PATH |

> O script exibe avisos no terminal caso alguma ferramenta não seja encontrada.


## Instalação rápida

### Linux / macOS

```bash
bash install.sh
```

### Windows

Execute no **PowerShell como Administrador**:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

> Ambos os scripts instalam as dependências do sistema, fazem o download do Poppler se necessário, instalam o `uv` e executam `uv sync` automaticamente.

---

### Instalação manual

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
