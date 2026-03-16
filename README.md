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

## Fluxo atual de funcionamento

1. **Escolha de Formato do ISBN:** Ao iniciar, o script pergunta via terminal se o ISBN salvo internamente deve ser `"limpo"` (apenas números) ou `"formatado"` (com hifens).
2. **Seleção do Alvo:** Você pode processar um único arquivo ou todos os livros de uma pasta inteira.
3. **Busca nas Tags do Documento (Primeira Etapa do Processamento):** O sistema examina se o arquivo já possui Título e Autor preenchidos em seus metadados internos. Se houver, ele exibe essas informações e pergunta se você deseja renomear o arquivo imediatamente usando apenas esses dados (poupando a busca por ISBN nas etapas seguintes).
4. **Busca Focada em "Folha de Créditos":** Caso a busca por tags falhe ou seja ignorada, o script avalia primeiramente a página 4 do documento (onde tipicamente fica a folha de rosto/créditos). Se achar informações úteis, tenta extrair de imediato o ISBN e o **Ano de Publicação** diretamente dali.
5. **Extração Ampla de ISBN:** Se a folha de créditos não bastar, o script amplia a procura pelo ISBN no texto do arquivo:
   - **PDF:** Usa o `pdfminer` (texto) para ler as 10 primeiras e as 10 últimas páginas. Se o ISBN não for localizado, aciona OCR de alta definição (600 DPI) com `pytesseract` (com suporte as últimas páginas do PDF) aliado a pré-processamento de imagem automático.
   - **EPUB:** Usa `ebooklib` + `BeautifulSoup` para examinar o texto interno à procura do ISBN (também verificando os 10 primeiros e os 10 últimos documentos do EPUB).
6. **Pesquisa em APIs (CBL, Google Books e Open Library):**
   - O projeto pesquisa os metadados do livro nas plataformas. Se extraiu o ISBN com sucesso, busca via ISBN.
   - Se o ISBN original **não** existir no texto do livro, ele usa as informações de Título/Autor (obtidas no passo 3) como _fallback_ realizando busca direta pelas bases on-line.
7. **Intervenção Manual (Fallback Final):** Caso as buscas automáticas não obtenham sucesso absoluto, o script avisa no terminal e aguarda você digitar manualmente um ISBN ou termo de Título/Autor para nova tentativa de pesquisa.
8. **Gravação e Renomeio Final:** Após obter o Título e o Autor limpos e oficiais (e o Ano, se disponível), o script injeta os novos metadados definitivamente nas propriedades do arquivo longo (via Python nativo ou `exiftool`) com a tag *Date/CreateDate* e renomeia-o numeração e padronização impecável: `Título - Autor - Ano.ext` (ou apenas sem o ano se ele não foi encontrado em nenhuma etapa).


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
