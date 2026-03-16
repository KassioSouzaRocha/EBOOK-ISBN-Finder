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


# Controle global de formato ISBN
FORMATO_ISBN: str = "limpo"  # "limpo" (só dígitos) ou "formatado" (com hífens)


def formatar_isbn(isbn_bruto: str) -> str:
    """Aplica o formato configurado ao ISBN.

    Se FORMATO_ISBN == 'formatado', preserva hífens do original.
    Caso contrário, retorna somente dígitos.
    """
    limpo = re.sub(r"[^0-9X]", "", isbn_bruto.upper())
    if FORMATO_ISBN == "formatado":
        # Tenta formatar ISBN-13: 978-XX-XXXX-XXX-X
        if len(limpo) == 13:
            return f"{limpo[:3]}-{limpo[3:5]}-{limpo[5:9]}-{limpo[9:12]}-{limpo[12]}"
        # ISBN-10: X-XXXX-XXXX-X
        elif len(limpo) == 10:
            return f"{limpo[0]}-{limpo[1:5]}-{limpo[5:9]}-{limpo[9]}"
    return limpo


def extrair_isbn_do_texto(texto: str) -> str | None:
    """Localiza o ISBN no texto e retorna no formato configurado."""
    if not texto:
        return None
    padrao = r"(?i)ISBN(?:-1[03])?:?\s*((?:97[89][\s\-]?)?(?:\d[\s\-]?){9}[\dX])"
    match = re.search(padrao, texto)
    if match:
        isbn_bruto = match.group(1).strip()
        return formatar_isbn(isbn_bruto)
    return None


def processar_imagem_ocr(imagem: Image.Image) -> Image.Image:
    """Aplica pré-processamento na imagem para melhorar a leitura do OCR."""
    imagem = imagem.convert("L")
    imagem = ImageOps.autocontrast(imagem)
    imagem = imagem.point(lambda x: 0 if x < 128 else 255, "1")
    return imagem


from pdf2image import convert_from_path, pdfinfo_from_path

def realizar_ocr_hd(caminho_pdf: str) -> str:
    """Realiza OCR em alta definição (600 DPI) nas primeiras e últimas 10 páginas do PDF."""
    logger.info("[OCR HD] Analisando 10 primeiras páginas em 600 DPI...")
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
            
        # Se encontrou nas primeiras, nem gasta tempo com as ultimas
        if extrair_isbn_do_texto(texto_total):
             return texto_total
             
        # Se não encontrou, buscar nas ultimas 10
        try:
            info = pdfinfo_from_path(caminho_pdf, poppler_path=POPPLER_PATH)
            total_paginas = info["Pages"]
            if total_paginas > 10:
                logger.info(f"[OCR HD] Analisando 10 últimas páginas (de {total_paginas}) em 600 DPI...")
                first_last = max(11, total_paginas - 9)
                paginas_finais = convert_from_path(
                    caminho_pdf,
                    first_page=first_last,
                    last_page=total_paginas,
                    dpi=600,
                    poppler_path=POPPLER_PATH,
                )
                for pg in paginas_finais:
                    pg_otimizada = processar_imagem_ocr(pg)
                    texto_total += pytesseract.image_to_string(pg_otimizada, config="--psm 3")
        except Exception as e:
            logger.debug("[OCR HD] Erro ao analisar as últimas páginas: %s", e)
            
        return texto_total
    except Exception as e:
        logger.warning("[OCR HD] Falhou: %s", e)
        return ""


# --- BUSCA DE METADADOS ---

def obter_metadados_arquivo(caminho: str) -> dict:
    """Extrai metadados existentes (título e autor) do arquivo."""
    ext = os.path.splitext(caminho)[1].lower()
    dados = {"titulo": "", "autor": ""}
    
    try:
        if ext == ".epub":
            livro = epub.read_epub(caminho)
            dados["titulo"] = livro.get_metadata("DC", "title")[0][0] if livro.get_metadata("DC", "title") else ""
            dados["autor"] = livro.get_metadata("DC", "creator")[0][0] if livro.get_metadata("DC", "creator") else ""
        else:
            # PDF e MOBI via exiftool
            resultado = subprocess.run(
                ["exiftool", "-s3", "-Title", "-Author", caminho],
                capture_output=True, text=True
            )
            linhas = resultado.stdout.splitlines()
            if len(linhas) >= 1: dados["titulo"] = linhas[0].strip()
            if len(linhas) >= 2: dados["autor"] = linhas[1].strip()
    except Exception:
        pass
    return dados


def obter_metadados_completos(isbn: str, titulo_sugerido: str = "", autor_sugerido: str = "") -> dict | None:
    """Busca resiliente de metadados em múltiplas fontes."""
    isbn_limpo = re.sub(r"[^0-9X]", "", isbn.upper()) if isbn else ""
    logger.info("   Pesquisando metadados para: %s %s", isbn if isbn else "", f"({titulo_sugerido})" if titulo_sugerido else "")

    # Variantes de ISBN
    variantes = [isbn_limpo] if isbn_limpo else []
    
    # 1. CBL — API Azure Cognitive Search
    cbl_url = "https://isbn-search-br.search.windows.net/indexes/isbn-index/docs/search?api-version=2021-04-30-Preview"
    cbl_headers = {
        "api-key": "100216A23C5AEE390338BBD19EA86D29",
        "Content-Type": "application/json",
    }
    
    # Tenta primeiro por ISBN, depois por Título/Autor
    buscas = []
    if isbn_limpo:
        buscas.append({"q": isbn_limpo, "fields": "RowKey,FormattedKey"})
    if titulo_sugerido:
        termos = f"{titulo_sugerido} {autor_sugerido}".strip()
        buscas.append({"q": termos, "fields": "Title,AuthorsStr"})

    for busca in buscas:
        try:
            body = {
                "search": busca["q"],
                "searchFields": busca["fields"],
                "top": 1,
                "select": "Title,Subtitle,AuthorsStr,Authors,Imprint,RowKey,FormattedKey",
            }
            resposta = requests.post(cbl_url, headers=cbl_headers, json=body, timeout=10)
            resposta.raise_for_status()
            dados = resposta.json()
            resultados = dados.get("value", [])
            logger.debug("Raw CBL Response: %s", dados)

            if resultados:
                item = resultados[0]
                titulo = item.get("Title", "S/T")
                subtitulo = item.get("Subtitle")
                if subtitulo:
                    titulo = f"{titulo} -- {subtitulo}"
                
                # Prioridade: AuthorsStr > Authors (lista/string)
                autor = item.get("AuthorsStr")
                if not autor:
                    authors_field = item.get("Authors")
                    if isinstance(authors_field, list):
                        autor = ", ".join(authors_field)
                    elif isinstance(authors_field, str):
                        autor = authors_field

                return {
                    "titulo": titulo,
                    "autor": (autor or "S/A").strip(),
                    "editora": (item.get("Imprint") or item.get("Publisher") or "S/E").strip(),
                }
        except Exception as e:
            logger.debug("Falha na busca CBL (%s): %s", busca["q"], e)

    # 2. Google Books
    if isbn_limpo:
        try:
            url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_limpo}"
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
        except Exception as e:
            logger.debug("Google Books indisponível: %s", e)

    # 3. Open Library (API JSON — cobertura internacional)
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
    print(f"\n  [AVISO] {motivo}")
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
    
    # Extrair metadados existentes para ajudar na busca
    meta_inicial = obter_metadados_arquivo(caminho)

    titulo_meta = meta_inicial.get("titulo", "").strip()
    autor_meta = meta_inicial.get("autor", "").strip()
    
    if titulo_meta or autor_meta:
        print("\n  [METADADOS ENCONTRADOS NAS TAGS DO ARQUIVO]")
        print(f"    Titulo: {titulo_meta or 'N/A'}")
        print(f"    Autor:  {autor_meta or 'N/A'}")
        escolha = input("  Deseja renomear o arquivo usando apenas essas informacoes? (s/n) [padrao: n]: ").strip().lower()
        if escolha == "s":
            dados = {
                "titulo": titulo_meta or "Sem Titulo",
                "autor": autor_meta or "Sem Autor",
                "editora": "S/E"
            }
            novo = gravar_e_renomear(caminho, dados, ext)
            logger.info("   Sucesso (metadados locais): %s", novo)
            return

    from pdf2image import pdfinfo_from_path
    if ext == ".pdf":
        try:
            isbn = extrair_isbn_do_texto(extract_text(caminho, page_numbers=list(range(10))))
            if not isbn:
                try:
                    info = pdfinfo_from_path(caminho, poppler_path=POPPLER_PATH)
                    total_paginas = info["Pages"]
                    if total_paginas > 10:
                        first_last = max(10, total_paginas - 10)
                        paginas_finais = list(range(first_last, total_paginas))
                        texto_final = extract_text(caminho, page_numbers=paginas_finais)
                        isbn = extrair_isbn_do_texto(texto_final)
                except Exception as e:
                    logger.debug("Falha ao ler ultimas paginas com pdfminer: %s", e)
        except Exception as e:
            logger.debug("Extração de texto via pdfminer falhou: %s", e)
        if not isbn:
            isbn = extrair_isbn_do_texto(realizar_ocr_hd(caminho))

    elif ext == ".epub":
        try:
            livro = epub.read_epub(caminho)
            texto = ""
            itens = list(livro.get_items_of_type(ITEM_DOCUMENT))
            
            # Lê os primeiros 10 documentos
            for item in itens[:10]:
                texto += BeautifulSoup(item.get_content(), "lxml").get_text()
            isbn = extrair_isbn_do_texto(texto)
            
            # Lê os últimos 10 se não achou e houver mais itens
            if not isbn and len(itens) > 10:
                texto_final = ""
                for item in itens[-10:]:
                    texto_final += BeautifulSoup(item.get_content(), "lxml").get_text()
                isbn = extrair_isbn_do_texto(texto_final)
        except Exception as e:
            logger.warning("Falha ao ler EPUB '%s': %s", nome_arq, e)

    # Busca principal (pelo ISBN ou Metadados extraídos)
    dados = None
    if isbn:
        dados = obter_metadados_completos(isbn, meta_inicial["titulo"], meta_inicial["autor"])
    elif meta_inicial["titulo"]:
        logger.info("   ISBN não encontrado. Tentando busca por Título/Autor...")
        dados = obter_metadados_completos(None, meta_inicial["titulo"], meta_inicial["autor"])

    if dados:
        novo = gravar_e_renomear(caminho, dados, ext)
        logger.info("   Sucesso: %s", novo)
    else:
        # Fallback manual
        logger.warning("   Dados não localizados automaticamente.")
        isbn_manual = solicitar_isbn_manual("Informe o ISBN ou Título/Autor para busca manual.")
        if isbn_manual:
            # Se o usuário digitar algo que não parece um ISBN, tratamos como título
            if re.search(r"[a-zA-Z]{3,}", isbn_manual):
                dados = obter_metadados_completos(None, isbn_manual, "")
            else:
                dados = obter_metadados_completos(isbn_manual)
            
            if dados:
                novo = gravar_e_renomear(caminho, dados, ext)
                logger.info("   Sucesso (manual): %s", novo)
            else:
                logger.warning("   Busca manual sem resultados. Pulando.")


def _escolher_formato_isbn() -> None:
    """Menu interativo para o usuário escolher o formato do ISBN."""
    global FORMATO_ISBN
    print("\n" + "=" * 50)
    print("   [ISBN RENAMER] - Formato do ISBN")
    print("=" * 50)
    print("\n  Escolha o formato de exibicao do ISBN:\n")
    print("   [1] Limpo (so digitos)     -> 9788535914849")
    print("   [2] Formatado (com hifens) -> 978-85-359-1484-9")
    print()
    while True:
        escolha = input("  Opcao (1 ou 2) [padrao: 1]: ").strip()
        if escolha in ("", "1"):
            FORMATO_ISBN = "limpo"
            print("\n  [OK] Formato: ISBN limpo (so digitos)\n")
            break
        elif escolha == "2":
            FORMATO_ISBN = "formatado"
            print("\n  [OK] Formato: ISBN formatado (com hifens)\n")
            break
        else:
            print("  [ERRO] Opcao invalida. Digite 1 ou 2.")


def iniciar():
    """Ponto de entrada: processa arquivo único ou todos os livros da pasta."""
    _escolher_formato_isbn()
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