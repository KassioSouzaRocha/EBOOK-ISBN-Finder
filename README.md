# ISBN Renamer

Ferramenta CLI para processar bibliotecas de livros digitais (PDF, EPUB, MOBI): extrai o ISBN de cada arquivo, busca título, autor e editora nas APIs da CBL (Azure Cognitive Search), Google Books e Open Library, e renomeia os arquivos automaticamente no formato `Título - Autor.ext`.

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
git clone <url-do-repo>
cd isbn-renamer
uv sync
```

## Uso

### Via terminal

```bash
# Abrir diálogo gráfico para escolher arquivo ou pasta
uv run isbn.py

# Processar um único arquivo
uv run isbn.py --arquivo "Livro.pdf"

# Processar todos os livros de uma pasta
uv run isbn.py --pasta ~/Livros/
```

### Argumentos CLI

| Argumento | Descrição |
|---|---|
| `--arquivo FILE` | Processa um único arquivo (PDF, EPUB ou MOBI) |
| `--pasta DIR` | Processa todos os livros da pasta indicada |
| _(sem argumento)_ | Abre diálogo gráfico com opção de escolher arquivo ou pasta |

### Via menu de contexto (clique-direito)

Após a instalação, o menu de contexto aparece ao clicar com o botão direito em arquivos ou pastas no gerenciador de arquivos:

| Desktop | Onde aparece | Opções |
|---|---|---|
| **GNOME (Nautilus)** | Scripts → | **"Somente esse item — Renomear com ISBN"** · **"Renomear com ISBN"** |
| **KDE (Dolphin)** | Renomear com ISBN → | **"Somente esse item"** · **"Pasta inteira"** |
| **Windows Explorer** | Renomear com ISBN → | **"Somente esse item"** · **"Pasta inteira"** |
| **macOS (Finder)** | Quick Action → | **"Renomear com ISBN"** |

> **Dica:** após a instalação, reinicie o gerenciador de arquivos (`nautilus -q` no GNOME) para que as novas entradas apareçam.

## Pipeline de extração

```
Arquivo PDF  →  pdfminer (texto)  →  ISBN encontrado?
                       ↓ não
             OCR 600 DPI (pytesseract)  →  ISBN encontrado?
                       ↓ não
             "ISBN não localizado nas 10 páginas"

Arquivo EPUB →  ebooklib + BeautifulSoup  →  ISBN encontrado?
```

Após a extração do ISBN:

```
ISBN → CBL API (Azure Cognitive Search) → título + autor + editora?
              ↓ não
       Google Books API → encontrou?
              ↓ não
       Open Library API → encontrou?
              ↓ não
       "Metadados não encontrados"
              ↓ sim
       Grava metadados no arquivo (exiftool) → Renomeia para "Título - Autor.ext"
```

## Estrutura do projeto

```
ISBN/
├── isbn.py                             # Script principal
├── pyproject.toml                      # Dependências Python (uv/pip)
├── install.sh                          # Instalador Linux/macOS
├── install.ps1                         # Instalador Windows
├── context_menu/
│   ├── nautilus_script                 # Script Nautilus (GNOME)
│   ├── isbn-renamer.desktop            # Service Menu KDE (Dolphin)
│   ├── register_windows.ps1            # Registro do menu de contexto Windows
│   └── create_macos_quickaction.sh     # Quick Action macOS (Finder)
└── README.md
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
