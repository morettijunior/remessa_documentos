import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote

def formatar_moeda(valor):
    if not valor:
        return "0,00"
    val_str = f"{float(valor):,.2f}"
    return val_str.replace(",", "X").replace(".", ",").replace("X", ".")

def limpar_telefone(telefone):
    """Limpa e formata o telefone para o padrão internacional (DDI 55 + DDD + Numero)"""
    if not telefone:
        return None
    digitos = "".join([c for c in str(telefone) if c.isdigit()])
    if len(digitos) < 10:
        return None
    if not digitos.startswith("55"):
        digitos = "55" + digitos
    return digitos

def enviar_whatsapp_cobranca(dados_pedido, arquivos_encontrados):
    """
    Envia a cobrança (mensagem formatada + anexos) via WhatsApp Web utilizando Selenium e Microsoft Edge.
    Utiliza uma pasta de perfil local isolada para manter a sessão (não pede QR Code após o primeiro login).
    """
    telefone_raw = dados_pedido.get("WHATSAPP") or dados_pedido.get("TELEFONE")
    telefone = limpar_telefone(telefone_raw)
    
    if not telefone:
        raise ValueError(f"O cliente {dados_pedido.get('CLIENTE_NOME')} não possui um número de WhatsApp/Telefone válido cadastrado.")
    
    cliente_nome = dados_pedido.get("CLIENTE_NOME", "Cliente")
    numero_pedido = dados_pedido.get("NUMERO_PEDIDO", "")
    os_valor = dados_pedido.get("OS")
    placa = dados_pedido.get("PLACA", "")
    
    # Montagem do Texto otimizado para leitura no WhatsApp
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
        f"Estamos encaminhando os documentos {referencia_texto} da *RONDOCHASSIS*.\n"
        f"Abaixo estão os detalhes para pagamento:\n"
        f"{detalhes_boletos_txt}\n\n"
        f"Em anexo seguem os arquivos (Pedido, Nota Fiscal e Boleto).\n"
        f"Qualquer dúvida, estamos à disposição!\n"
        f"_RONDOCHASSIS SERVIÇOS LTDA_"
    )

    # Coleta todos os arquivos válidos do dicionário para anexar
    arquivos_para_enviar = []
    
    def adicionar_arquivo(caminho):
        if caminho:
            p = Path(caminho)
            if p.exists():
                arquivos_para_enviar.append(str(p.resolve()))

    adicionar_arquivo(arquivos_encontrados.get("PEDIDO"))
    adicionar_arquivo(arquivos_encontrados.get("NFS_PDF"))
    adicionar_arquivo(arquivos_encontrados.get("NFE_PDF"))
    adicionar_arquivo(arquivos_encontrados.get("NFE_XML"))
    
    for b_path in arquivos_encontrados.get("BOLETOS", []):
        adicionar_arquivo(b_path)

    if not arquivos_para_enviar:
        print("⚠️ Aviso: Nenhum arquivo foi encontrado para anexar no WhatsApp, mas a mensagem de texto será enviada.")

    # Configuração do Selenium com Microsoft Edge e Perfil Persistente Isolado
    pasta_perfil = Path.home() / "Documents" / "RemessaDocumentos" / "WhatsappSessionEdge"
    pasta_perfil.mkdir(parents=True, exist_ok=True)

    options = webdriver.EdgeOptions()
    options.add_argument(f"user-data-dir={pasta_perfil}")
    options.add_argument("--start-maximized")

    print(f"Iniciando navegador Microsoft Edge para disparo no WhatsApp para o número {telefone}...")
    
    driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)
    
    try:
        link_zap = f"https://web.whatsapp.com/send?phone={telefone}&text={quote(mensagem)}"
        driver.get(link_zap)
        
        wait = WebDriverWait(driver, 60) # Aguarda até 60 segundos para carregar/ler QR Code se for a primeira vez
        
        print("Aguardando o WhatsApp Web carregar a conversa...")
        botao_enviar_texto = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]'))
        )
        
        botao_enviar_texto.click()
        time.sleep(2)
        
        if arquivos_para_enviar:
            print(f"Anexando {len(arquivos_para_enviar)} arquivo(s)...")
            
            clip_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//div[@title="Anexar" or @aria-label="Anexar"]'))
            )
            clip_button.click()
            time.sleep(1)
            
            for arquivo in arquivos_para_enviar:
                file_input = driver.find_element(By.XPATH, '//input[@type="file" and (@accept="*") or @multiple]')
                file_input.send_keys(arquivo)
                time.sleep(2)
            
            botao_enviar_midia = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send" or @data-icon="checkmark"]'))
            )
            botao_enviar_midia.click()
            print("Arquivos anexados e enviados com sucesso!")
            time.sleep(3)

        print(f"✅ WhatsApp enviado com sucesso para {cliente_nome} ({telefone})!")
        return True

    except Exception as e:
        raise Exception(f"Erro na automação do WhatsApp Web (Edge): {str(e)}")
    finally:
        driver.quit()