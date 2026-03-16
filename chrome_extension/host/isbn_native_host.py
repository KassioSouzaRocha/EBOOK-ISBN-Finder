#!/usr/bin/env python3
import sys
import json
import struct
import os
import logging

# Configuração de log para debug da extensão (Chrome não exibe stderr do host)
logging.basicConfig(filename='/tmp/isbn_renamer_host.log', level=logging.INFO, 
                    format='%(asctime)s %(levelname)s: %(message)s')

# Adiciona o diretório superior ao path para importar o isbn.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import isbn

def get_message():
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        return None
    msg_length = struct.unpack('@I', raw_length)[0]
    message = sys.stdin.buffer.read(msg_length).decode('utf-8')
    return json.loads(message)

def send_message(msg):
    encoded_msg = json.dumps(msg).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('@I', len(encoded_msg)))
    sys.stdout.buffer.write(encoded_msg)
    sys.stdout.buffer.flush()

if __name__ == '__main__':
    logging.info("Native Host iniciado.")
    # Força modo limpo no import
    isbn.FORMATO_ISBN = "limpo"
    
    while True:
        try:
            msg = get_message()
            if msg is None:
                break
            
            logging.info(f"Mensagem recebida: {msg}")
            if msg.get('action') == 'process_file':
                filepath = msg.get('path')
                if filepath and os.path.exists(filepath):
                    # Define stdout e stderr para devnull para nao corromper native messaging
                    old_stdout = sys.stdout
                    sys.stdout = open(os.devnull, 'w')
                    try:
                        isbn._processar_arquivo(filepath, interativo=False)
                    except Exception as e:
                        logging.error(f"Erro ao processar: {e}")
                    finally:
                        sys.stdout.close()
                        sys.stdout = old_stdout
                    
                    send_message({"status": "concluido", "file": filepath})
                else:
                    logging.warning(f"Arquivo nao encontrado: {filepath}")
                    send_message({"status": "erro", "error": "Arquivo nao encontrado"})
        except Exception as e:
            logging.error(f"Erro critico: {e}")
            break
