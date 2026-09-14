import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote

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

def enviar_whatsapp_cobranca(dados_pedido, arquivos_encontrados=None, driver_instancia=None):
    """
    Envia a notificação profissional de cobrança via WhatsApp Web (sem anexos),
    informando que as notas e boletos foram enviados por e-mail.
    Suporta reutilização de instância do navegador para disparos em lote.
    """
    telefone_raw = dados_pedido.get("WHATSAPP") or dados_pedido.get("TELEFONE")
    telefone = limpar_telefone(telefone_raw)
    
    if not telefone:
        raise ValueError(f"O cliente {dados_pedido.get('CLIENTE_NOME')} não possui um número válido cadastrado.")
    
    cliente_nome = dados_pedido.get("CLIENTE_NOME", "Cliente")
    numero_pedido = dados_pedido.get("NUMERO_PEDIDO", "")
    os_valor = dados_pedido.get("OS")
    placa = dados_pedido.get("PLACA", "")
    cliente_email = dados_pedido.get("EMAIL", "seu e-mail")
    
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
        f"Informamos que as notas fiscais, XMLs e boletos {referencia_texto} da *RONDOCHASSIS* foram enviados para o seu e-mail cadastrado (*{cliente_email}*).\n\n"
        f"Abaixo estão os detalhes para pagamento:\n"
        f"{detalhes_boletos_txt}\n\n"
        f"Qualquer dúvida ou se precisar de novos arquivos, estamos à disposição!\n"
        f"_RONDOCHASSIS SERVIÇOS LTDA_"
    )

    driver = driver_instancia
    fechar_ao_final = False

    if not driver:
        pasta_perfil = Path.home() / "Documents" / "RemessaDocumentos" / "WhatsappSessionEdge"
        pasta_perfil.mkdir(parents=True, exist_ok=True)

        options = webdriver.EdgeOptions()
        options.add_argument(f"user-data-dir={pasta_perfil}")
        options.add_argument("--start-maximized")

        print(f"Iniciando Microsoft Edge para envio do aviso via WhatsApp para {telefone}...")
        driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)
        fechar_ao_final = True

    try:
        link_zap = f"https://web.whatsapp.com/send?phone={telefone}&text={quote(mensagem)}"
        driver.get(link_zap)
        
        wait = WebDriverWait(driver, 60)
        
        print("Aguardando a caixa de texto carregar...")
        caixa_texto = wait.until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
        )
        time.sleep(2.5)
        
        # Pressiona ENTER na caixa de texto para disparar a mensagem estruturada
        caixa_texto.send_keys(Keys.ENTER)
        print("✔ Mensagem informativa enviada com sucesso no WhatsApp!")
        time.sleep(4) # Pausa para consolidar o envio na rede

        print(f"✅ Disparo de WhatsApp concluído!")
        return True

    except Exception as e:
        raise Exception(f"Erro na automação do WhatsApp Web (Edge): {str(e)}")
    finally:
        if fechar_ao_final and driver:
            time.sleep(3)
            driver.quit()