import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import warnings

import pytesseract
import requests
from bs4 import BeautifulSoup
from ebooklib import epub, ITEM_DOCUMENT
from pdf2image import convert_from_path
from pdfminer.high_level import extract_text
from PIL import Image, ImageOps
from tkinter import Tk, filedialog

warnings.filterwarnings("ignore", category=UserWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


# --- CONFIGURAÇÃO DE PLATAFORMA ---

def _detectar_poppler_windows() -> str | None:
    """Tenta localizar o Poppler em caminhos típicos do Windows."""
    candidatos = [
        r"C:\\Program Files\\poppler\\Library\\bin",
        r"C:\\poppler\\Library\\bin",
        r"C:\\poppler\\bin",
    ]
    # Busca também qualquer pasta 'poppler-*' em Program Files
    for raiz in (r"C:\\Program Files", r"C:\\Program Files (x86)", r"C:\\"):
        try:
            for item in os.listdir(raiz):
                if item.lower().startswith("poppler"):
                    candidatos.insert(0, os.path.join(raiz, item, "Library", "bin"))
                    candidatos.insert(0, os.path.join(raiz, item, "bin"))
        except OSError:
            pass
    for caminho in candidatos:
        if os.path.isfile(os.path.join(caminho, "pdftoppm.exe")):
            return caminho
    return None


def configurar_plataforma() -> str | None:
    """Configura ferramentas externas conforme o sistema operacional.

    Returns:
        Caminho do Poppler (Windows) ou None (Linux/macOS, usa PATH).
    """
    poppler_path = None

    if sys.platform == "win32":
        # --- Tesseract ---
        tesseract_exe = shutil.which("tesseract")
        if not tesseract_exe:
            caminho_padrao = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            if os.path.isfile(caminho_padrao):
                tesseract_exe = caminho_padrao
        if tesseract_exe:
            pytesseract.pytesseract.tesseract_cmd = tesseract_exe
            logger.info("Tesseract: %s", tesseract_exe)
        else:
            logger.warning(
                "Tesseract não encontrado. Instale em https://github.com/UB-Mannheim/tesseract/wiki "
                "e adicione ao PATH (ou instale em C:\\Program Files\\Tesseract-OCR)."
            )

        # --- Poppler ---
        if shutil.which("pdftoppm"):
            logger.info("Poppler: encontrado no PATH")
        else:
            poppler_path = _detectar_poppler_windows()
            if poppler_path:
                logger.info("Poppler: %s", poppler_path)
            else:
                logger.warning(
                    "Poppler não encontrado. Baixe em https://github.com/oschwartz10612/poppler-windows/releases "
                    "e extraia em C:\\Program Files\\poppler (ou adicione ao PATH)."
                )

        # --- ExifTool ---
        if not shutil.which("exiftool"):
            logger.warning(
                "ExifTool não encontrado. Baixe em https://exiftool.org e adicione ao PATH."
            )

    return poppler_path


POPPLER_PATH = configurar_plataforma()


# --- EXTRAÇÃO DE ISBN ---

def obter_alvo() -> tuple[str, str]:
    """Retorna (modo, caminho) indicando o que processar.

    Modos possíveis:
      - ``'arquivo'``: processa um único arquivo (``--arquivo``).
      - ``'pasta'``:   processa todos os livros da pasta (``--pasta`` ou diálogo).

    Prioridade:
      1. ``--arquivo CAMINHO``  — passado pelo menu de contexto ao selecionar arquivo.
      2. ``--pasta DIR``        — passado pelo menu de contexto ao selecionar pasta.
      3. Diálogo gráfico Tkinter com opção de escolher arquivo ou pasta.
    """
    ap = argparse.ArgumentParser(
        description="ISBN Renamer — renomeia livros usando metadados do ISBN.",
        add_help=False,
    )
    ap.add_argument(
        "--arquivo",
        metavar="FILE",
        default=None,
        help="Arquivo único a processar (pdf, epub ou mobi).",
    )
    ap.add_argument(
        "--pasta",
        metavar="DIR",
        default=None,
        help="Pasta com os livros a processar (opcional; abre diálogo se omitido).",
    )
    args, _ = ap.parse_known_args()

    if args.arquivo:
        return ("arquivo", args.arquivo)
    if args.pasta:
        return ("pasta", args.pasta)

    # Fallback: diálogo gráfico — pergunta ao usuário se quer arquivo ou pasta
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    from tkinter import messagebox
    escolha = messagebox.askyesno(
        "ISBN Renamer",
        "Deseja selecionar um arquivo específico?\n\n"
        "  Sim  → seleciona um arquivo\n"
        "  Não  → seleciona uma pasta inteira",
    )
    if escolha:
        formatos = [("Livros", "*.pdf *.epub *.mobi"), ("Todos", "*.*")]
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo do livro",
            filetypes=formatos,
        )
        root.destroy()
        return ("arquivo", caminho) if caminho else ("pasta", "")
    else:
        caminho = filedialog.askdirectory(title="Selecione a pasta dos livros")
        root.destroy()
        return ("pasta", caminho) if caminho else ("pasta", "")


def extrair_isbn_do_texto(texto: str) -> str | None:
    """Localiza o ISBN no texto e retorna somente dígitos (sem espaços/hífens)."""
    if not texto:
        return None
    padrao = r"(?i)ISBN(?:-1[03])?:?\s*((?:97[89][\s\-]?)?(?:\d[\s\-]?){9}[\dX])"
    match = re.search(padrao, texto)
    if match:
        isbn_bruto = match.group(1).strip()
        return re.sub(r"[^0-9X]", "", isbn_bruto.upper())
    return None


def processar_imagem_ocr(imagem: Image.Image) -> Image.Image:
    """Aplica pré-processamento na imagem para melhorar a leitura do OCR."""
    imagem = imagem.convert("L")
    imagem = ImageOps.autocontrast(imagem)
    imagem = imagem.point(lambda x: 0 if x < 128 else 255, "1")
    return imagem


def realizar_ocr_hd(caminho_pdf: str) -> str:
    """Realiza OCR em alta definição (600 DPI) nas primeiras 10 páginas do PDF."""
    logger.info("[OCR HD] Analisando 10 páginas em 600 DPI...")
    try:
        paginas = convert_from_path(
            caminho_pdf,
            first_page=1,
            last_page=10,
            dpi=600,
            poppler_path=POPPLER_PATH,  # None no Linux/macOS (usa PATH)
        )
        texto_total = ""
        for pg in paginas:
            pg_otimizada = processar_imagem_ocr(pg)
            texto_total += pytesseract.image_to_string(pg_otimizada, config="--psm 3")
        return texto_total
    except Exception as e:
        logger.warning("[OCR HD] Falhou: %s", e)
        return ""


# --- BUSCA DE METADADOS ---

def obter_metadados_completos(isbn: str) -> dict | None:
    """Busca resiliente de metadados em múltiplas fontes (Google Books, Open Library, CBL)."""
    isbn_limpo = re.sub(r"[^0-9X]", "", isbn.upper())
    isbn_original = isbn.strip()  # mantém hífens/formatação original
    # Variantes: primeiro sem hífens, depois com formatação original
    variantes = [isbn_limpo]
    if isbn_original != isbn_limpo:
        variantes.append(isbn_original)
    logger.info("   Pesquisando metadados para: %s", isbn)

    # 1. Google Books (API JSON — fonte mais confiável)
    for variante in variantes:
        try:
            url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{variante}"
            resposta = requests.get(url, timeout=10)
            resposta.raise_for_status()
            dados_json = resposta.json()
            if "items" in dados_json:
                info = dados_json["items"][0]["volumeInfo"]
                return {
                    "titulo": info.get("title", "S/T"),
                    "autor": ", ".join(info.get("authors", ["S/A"])),
                    "editora": info.get("publisher", "S/E"),
                }
        except requests.RequestException as e:
            logger.debug("Google Books indisponível (%s): %s", variante, e)
        except Exception as e:
            logger.warning("Erro inesperado ao consultar Google Books: %s", e)

    # 2. Open Library (API JSON — boa cobertura internacional)
    for variante in variantes:
        try:
            url = f"https://openlibrary.org/isbn/{variante}.json"
            resposta = requests.get(url, timeout=10)
            if resposta.status_code == 200:
                dados = resposta.json()
                titulo = dados.get("title", "S/T")
                editora = "S/E"
                if dados.get("publishers"):
                    editora = dados["publishers"][0]
                autor = "S/A"
                # Tenta autor direto na edição
                if dados.get("authors"):
                    try:
                        autor_key = dados["authors"][0].get("key", "")
                        if autor_key:
                            r = requests.get(f"https://openlibrary.org{autor_key}.json", timeout=5)
                            if r.status_code == 200:
                                autor = r.json().get("name", "S/A")
                    except Exception:
                        pass
                # Fallback: busca autor via /works/ (edições BR geralmente não têm authors direto)
                if autor == "S/A" and dados.get("works"):
                    try:
                        work_key = dados["works"][0]["key"]
                        rw = requests.get(f"https://openlibrary.org{work_key}.json", timeout=5)
                        if rw.status_code == 200:
                            work_data = rw.json()
                            if work_data.get("authors"):
                                autor_key = work_data["authors"][0].get("author", {}).get("key", "")
                                if autor_key:
                                    ra = requests.get(f"https://openlibrary.org{autor_key}.json", timeout=5)
                                    if ra.status_code == 200:
                                        autor = ra.json().get("name", "S/A")
                    except Exception:
                        pass
                return {"titulo": titulo, "autor": autor, "editora": editora}
        except requests.RequestException as e:
            logger.debug("Open Library indisponível (%s): %s", variante, e)
        except Exception as e:
            logger.warning("Erro inesperado ao consultar Open Library: %s", e)

    # 3. CBL (scraping — resultados carregados via JS, geralmente não funciona)
    placeholders = {"O Conto", "O Subtitle", ""}
    for variante in variantes:
        try:
            url = f"https://www.cblservicos.org.br/isbn/pesquisa/?page=1&filtro=isbn&q={variante}"
            resposta = requests.get(url, timeout=15)
            resposta.raise_for_status()
            soup = BeautifulSoup(resposta.text, "html.parser")
            titulo_tag = soup.find("h4")
            if titulo_tag:
                titulo = titulo_tag.get_text(strip=True)
                if titulo not in placeholders:
                    return {"titulo": titulo, "autor": "S/A", "editora": "S/E"}
        except requests.RequestException as e:
            logger.debug("CBL indisponível (%s): %s", variante, e)
        except Exception as e:
            logger.warning("Erro inesperado ao consultar CBL: %s", e)

    return None


# --- GESTÃO DE ARQUIVOS ---

def gravar_e_renomear(caminho: str, dados: dict, ext: str) -> str:
    """Grava metadados no arquivo e o renomeia com título e autor."""
    titulo = dados["titulo"][:80]
    autor = dados["autor"][:50]

    if ext == ".epub":
        try:
            livro = epub.read_epub(caminho)
            livro.set_unique_metadata("DC", "title", titulo)
            livro.set_unique_metadata("DC", "creator", autor)
            epub.write_epub(caminho, livro)
        except Exception as e:
            logger.warning("Não foi possível gravar metadados no EPUB: %s", e)
    else:
        resultado = subprocess.run(
            ["exiftool", f"-Title={titulo}", f"-Author={autor}", "-overwrite_original", caminho],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if resultado.returncode != 0:
            logger.warning("exiftool retornou código de erro para: %s", caminho)

    nome_base = f"{titulo} - {autor}"
    nome_limpo = re.sub(r'[\\/*?:"<>|\t\n\r\f\v]', "", nome_base)
    nome_limpo = re.sub(r"\s+", " ", nome_limpo).strip()
    novo_nome = f"{nome_limpo}{ext}"
    novo_caminho = os.path.join(os.path.dirname(caminho), novo_nome)

    if caminho != novo_caminho:
        try:
            os.rename(caminho, novo_caminho)
            return novo_nome
        except OSError as e:
            logger.error("Falha ao renomear '%s': %s", caminho, e)
            return os.path.basename(caminho)

    return os.path.basename(caminho)


# --- CORREÇÃO MANUAL ---

def solicitar_isbn_manual(motivo: str) -> str | None:
    """Solicita que o usuário informe um ISBN manualmente no terminal.

    Args:
        motivo: Mensagem descrevendo por que o ISBN precisa ser corrigido.

    Returns:
        O ISBN digitado (com hífens/espaços preservados) ou None se pulado.
    """
    print(f"\n  ⚠️  {motivo}")
    print("  Digite o ISBN correto (ou pressione Enter para pular): ", end="", flush=True)
    resposta = input().strip()
    if not resposta:
        logger.info("   Pulado pelo usuário.")
        return None
    return resposta


# --- PONTO DE ENTRADA ---

def _processar_arquivo(caminho: str) -> None:
    """Processa um único arquivo de livro: extrai ISBN, busca dados e renomeia."""
    nome_arq = os.path.basename(caminho)
    ext = os.path.splitext(nome_arq)[1].lower()
    formatos = (".pdf", ".epub", ".mobi")

    if ext not in formatos:
        logger.warning("Formato não suportado: %s", ext)
        return

    logger.info("\nProcessando: %s", nome_arq)
    isbn = None

    if ext == ".pdf":
        try:
            isbn = extrair_isbn_do_texto(extract_text(caminho, page_numbers=list(range(10))))
        except Exception as e:
            logger.debug("Extração de texto via pdfminer falhou: %s", e)
        if not isbn:
            isbn = extrair_isbn_do_texto(realizar_ocr_hd(caminho))

    elif ext == ".epub":
        try:
            livro = epub.read_epub(caminho)
            texto = ""
            for item in list(livro.get_items_of_type(ITEM_DOCUMENT))[:10]:
                texto += BeautifulSoup(item.get_content(), "lxml").get_text()
            isbn = extrair_isbn_do_texto(texto)
        except Exception as e:
            logger.warning("Falha ao ler EPUB '%s': %s", nome_arq, e)

    if isbn:
        dados = obter_metadados_completos(isbn)
        if dados:
            novo = gravar_e_renomear(caminho, dados, ext)
            logger.info("   Sucesso: %s", novo)
        else:
            logger.warning("   ISBN %s encontrado, mas sem dados nas APIs.", isbn)
            isbn_manual = solicitar_isbn_manual(
                f"ISBN '{isbn}' não retornou resultados nas APIs."
            )
            if isbn_manual:
                dados = obter_metadados_completos(isbn_manual)
                if dados:
                    novo = gravar_e_renomear(caminho, dados, ext)
                    logger.info("   Sucesso (manual): %s", novo)
                else:
                    logger.warning("   ISBN manual '%s' também sem resultados. Pulando.", isbn_manual)
    else:
        logger.warning("   ISBN não localizado nas 10 páginas.")
        isbn_manual = solicitar_isbn_manual("ISBN não encontrado automaticamente.")
        if isbn_manual:
            dados = obter_metadados_completos(isbn_manual)
            if dados:
                novo = gravar_e_renomear(caminho, dados, ext)
                logger.info("   Sucesso (manual): %s", novo)
            else:
                logger.warning("   ISBN manual '%s' sem resultados nas APIs. Pulando.", isbn_manual)


def iniciar():
    """Ponto de entrada: processa arquivo único ou todos os livros da pasta."""
    modo, alvo = obter_alvo()

    if not alvo:
        logger.warning("Nenhum alvo selecionado. Encerrando.")
        return

    if modo == "arquivo":
        if not os.path.isfile(alvo):
            logger.error("Arquivo não encontrado: %s", alvo)
            return
        _processar_arquivo(alvo)
        return

    # modo == "pasta"
    pasta = alvo
    formatos = (".pdf", ".epub", ".mobi")
    arquivos = sorted([f for f in os.listdir(pasta) if f.lower().endswith(formatos)])

    if not arquivos:
        logger.info("Nenhum arquivo encontrado na pasta: %s", pasta)
        return

    logger.info("Encontrados %d arquivo(s) para processar.", len(arquivos))

    for nome_arq in arquivos:
        caminho = os.path.join(pasta, nome_arq)
        _processar_arquivo(caminho)
        time.sleep(1)


if __name__ == "__main__":
    iniciar()