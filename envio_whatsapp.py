# ==============================================================================
# INSTRUÇÕES DE ACESSO E CONFIGURAÇÃO DA EVOLUTION API (RONDOCHASSIS)
# ==============================================================================
# Servidor Docker Local: http://servidor:8080 (ou http://localhost:8080 no servidor)
# Nome da Instância:     rondochassis
# API Key / Token:       RondoChassis2026*
# Painel Gerenciador:    http://servidor:8080/manager (para reconectar QR Code se necessário)
# ==============================================================================

import time
import base64
import requests
from pathlib import Path

def formatar_moeda(valor):
    if not valor:
        return "0,00"
    val_str = f"{float(valor):,.2f}"
    return val_str.replace(",", "X").replace(".", ",").replace("X", ".")

def limpar_telefone(telefone):
    if not telefone:
        return None
    digitos = "".join([c for c in str(telefone) if c.isdigit()])
    if len(digitos) < 10:
        return None
    if not digitos.startswith("55"):
        digitos = "55" + digitos
    return digitos

def enviar_whatsapp_cobranca(dados_pedido, arquivos_encontrados=None, config_whatsapp=None, enviar_com_anexos=False):
    """
    Envia a notificação de cobrança e os arquivos anexados (PDFs/XMLs) 
    via Evolution API hospedada localmente.
    """
    if not config_whatsapp:
        raise ValueError("As configurações da Evolution API (url_base, instance, apikey) não foram informadas.")

    url_base = config_whatsapp.get("url_base", "http://servidor:8080").rstrip("/")
    instance = config_whatsapp.get("instance", "rondochassis")
    apikey = config_whatsapp.get("apikey", "RondoChassis2026*")

    if not instance or not apikey:
        raise ValueError("O nome da 'instance' ou a 'apikey' da Evolution API estão faltando nas configurações.")

    telefone_raw = dados_pedido.get("WHATSAPP") or dados_pedido.get("TELEFONE")
    telefone = limpar_telefone(telefone_raw)
    
    if not telefone:
        raise ValueError(f"O cliente {dados_pedido.get('CLIENTE_NOME')} não possui um número de WhatsApp válido cadastrado.")
    
    cliente_nome = dados_pedido.get("CLIENTE_NOME", "Cliente")
    numero_pedido = dados_pedido.get("NUMERO_PEDIDO", "")
    os_valor = dados_pedido.get("OS")
    placa = dados_pedido.get("PLACA", "")
    
    if os_valor:
        referencia_texto = f"referente aos materiais e serviços prestados no veículo de placa {placa} (O.S. {os_valor})"
    else:
        referencia_texto = f"referente aos materiais entregues no pedido {numero_pedido}"
        
    boletos_dados = dados_pedido.get("BOLETOS", [])
    detalhes_boletos_txt = ""
    
    for idx, bol in enumerate(boletos_dados):
        parcela = bol.get("PARCELA", idx + 1)
        vencimento = bol.get("VENCIMENTO", "")
        venc_fmt = "/".join(vencimento.split("-")[::-1]) if "-" in vencimento else vencimento
        valor = formatar_moeda(bol.get("VALOR", 0.0))
        pix = bol.get("QRCODEPIX", "")
        linha_dig = bol.get("LINHADIGITAVELBOLETO", "")
        
        detalhes_boletos_txt += f"\n-----------------------------------\n"
        detalhes_boletos_txt += f"💳 *Parcela {parcela}* — Vencimento: *{venc_fmt}* — Valor: *R$ {valor}*\n"
        
        if linha_dig:
            detalhes_boletos_txt += f"🔢 *Linha Digitável:*\n`{linha_dig}`\n"
        if pix:
            detalhes_boletos_txt += f"🔗 *Pix Copia e Cole:*\n`{pix}`\n"

    mensagem = (
        f"Olá *{cliente_nome}*, tudo bem?\n\n"
        f"Informamos que as notas fiscais, XMLs e boletos {referencia_texto} da *RONDOCHASSIS* estão sendo encaminhados.\n\n"
        f"Abaixo estão os detalhes para pagamento:\n"
        f"{detalhes_boletos_txt}\n\n"
        f"Qualquer dúvida, estamos à disposição!\n"
        f"_RONDOCHASSIS SERVIÇOS LTDA_"
    )

    headers = {
        "apikey": apikey,
        "Content-Type": "application/json"
    }

    # 1. Envia a mensagem de texto principal
    url_texto = f"{url_base}/message/sendText/{instance}"
    payload_texto = {
        "number": telefone,
        "text": mensagem
    }

    try:
        resp = requests.post(url_texto, json=payload_texto, headers=headers, timeout=90)
        if resp.status_code not in [200, 201]:
            raise Exception(f"Erro HTTP {resp.status_code}: {resp.text}")
        print("✔ Mensagem de texto enviada via Evolution API!")
    except Exception as e:
        raise Exception(f"Erro ao conectar com a Evolution API (Texto): {str(e)}")

    # 2. Se a opção de anexar estiver ativada, envia os arquivos via sendMedia
    if enviar_com_anexos and arquivos_encontrados:
        lista_caminhos = []
        
        for tipo, caminho in arquivos_encontrados.items():
            if tipo == "BOLETOS" and isinstance(caminho, list):
                for b in caminho:
                    if b and Path(b).exists():
                        lista_caminhos.append(b)
            elif caminho and Path(caminho).exists():
                lista_caminhos.append(caminho)

        if lista_caminhos:
            url_media = f"{url_base}/message/sendMedia/{instance}"
            
            for arq_path in lista_caminhos:
                path_obj = Path(arq_path)
                print(f"📤 Enviando anexo: {path_obj.name}...")

                try:
                    # Converte o arquivo local para Base64
                    with open(path_obj, "rb") as f:
                        encoded_file = base64.b64encode(f.read()).decode("utf-8")

                    extensao = path_obj.suffix.lower()
                    mimetype = "application/pdf" if extensao == ".pdf" else "application/xml"

                    payload_media = {
                        "number": telefone,
                        "mediatype": "document",
                        "mimetype": mimetype,
                        "caption": f"Documento: {path_obj.name}",
                        "media": encoded_file,
                        "fileName": path_obj.name
                    }

                    resp_media = requests.post(url_media, json=payload_media, headers=headers, timeout=60)
                    if resp_media.status_code in [200, 201]:
                        print(f"✔ Arquivo {path_obj.name} enviado com sucesso!")
                    else:
                        print(f"⚠️ Erro ao enviar arquivo {path_obj.name}: {resp_media.text}")
                    
                    # Pequena pausa entre o envio de múltiplos arquivos para não sobrecarregar a fila do WhatsApp
                    time.sleep(1.5)

                except Exception as ex_media:
                    print(f"⚠️ Exceção ao processar o anexo {path_obj.name}: {ex_media}")

    return True