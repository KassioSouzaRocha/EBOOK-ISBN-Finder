import logging
import os
import re
import subprocess
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


# --- EXTRAÇÃO DE ISBN ---

def selecionar_pasta() -> str:
    """Abre diálogo gráfico para seleção da pasta com os livros."""
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    pasta = filedialog.askdirectory(title="Selecione a pasta dos livros")
    root.destroy()
    return pasta


def extrair_isbn_do_texto(texto: str, manter_formatacao: bool = True) -> str | None:
    """Localiza o ISBN no texto e mantém hífens/espaços se solicitado."""
    if not texto:
        return None
    padrao = r"(?i)ISBN(?:-1[03])?:?\s*((?:97[89][\s\-]?)?(?:\d[\s\-]?){9}[\dX])"
    match = re.search(padrao, texto)
    if match:
        isbn_bruto = match.group(1).strip()
        if manter_formatacao:
            return isbn_bruto
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
        paginas = convert_from_path(caminho_pdf, first_page=1, last_page=10, dpi=600)
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
    """Busca resiliente de metadados em múltiplas fontes (CBL, Google Books)."""
    isbn_limpo = re.sub(r"[^0-9X]", "", isbn.upper())
    logger.info("   Pesquisando metadados para: %s", isbn)

    # 1. Tenta CBL
    try:
        url = f"https://www.cblservicos.org.br/isbn/pesquisa/?page=1&q={isbn_limpo}"
        resposta = requests.get(url, timeout=15)
        resposta.raise_for_status()
        soup = BeautifulSoup(resposta.text, "html.parser")
        res = soup.find("div", class_="row-dados")
        if res:
            dados = {
                p.get_text().split(":")[0].strip().lower(): p.get_text().split(":")[1].strip()
                for p in res.find_all("p")
                if ":" in p.get_text()
            }
            return {
                "titulo": dados.get("título", "S/T"),
                "autor": dados.get("autor(es)", "S/A"),
                "editora": dados.get("editor", "S/E"),
            }
    except requests.RequestException as e:
        logger.debug("CBL indisponível: %s", e)
    except Exception as e:
        logger.warning("Erro inesperado ao consultar CBL: %s", e)

    # 2. Tenta Google Books
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_limpo}"
        resposta = requests.get(url, timeout=10)
        resposta.raise_for_status()
        dados_json = resposta.json()
        if "items" in dados_json:
            info = dados_json["items"][0]["volumeInfo"]
            return {
                "titulo": info.get("title", "S/T"),
                "autor": info.get("authors", ["S/A"])[0],
                "editora": info.get("publisher", "S/E"),
            }
    except requests.RequestException as e:
        logger.debug("Google Books indisponível: %s", e)
    except Exception as e:
        logger.warning("Erro inesperado ao consultar Google Books: %s", e)

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

def iniciar():
    """Processa todos os livros da pasta selecionada."""
    pasta = selecionar_pasta()
    if not pasta:
        logger.warning("Nenhuma pasta selecionada. Encerrando.")
        return

    formatos = (".pdf", ".epub", ".mobi")
    arquivos = sorted([f for f in os.listdir(pasta) if f.lower().endswith(formatos)])

    if not arquivos:
        logger.info("Nenhum arquivo encontrado na pasta: %s", pasta)
        return

    logger.info("Encontrados %d arquivo(s) para processar.", len(arquivos))

    for nome_arq in arquivos:
        caminho = os.path.join(pasta, nome_arq)
        ext = os.path.splitext(nome_arq)[1].lower()
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

        time.sleep(1)


if __name__ == "__main__":
    iniciar()