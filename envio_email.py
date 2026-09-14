import smtplib
import imaplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate, make_msgid
from pathlib import Path

def formatar_moeda(valor):
    if not valor:
        return "0,00"
    val_str = f"{float(valor):,.2f}"
    return val_str.replace(",", "X").replace(".", ",").replace("X", ".")

def enviar_email_cobranca(dados_pedido, arquivos_encontrados, config_email):
    """
    Envia boletos, notas fiscais, XMLs e pedido por e-mail via SMTP da Hostinger
    e grava uma cópia diretamente na pasta 'Sent' (Enviados) via IMAP.
    """
    cliente_nome = dados_pedido.get("CLIENTE_NOME", "Cliente")
    cliente_email = dados_pedido.get("EMAIL")
    
    if not cliente_email:
        raise ValueError("O cliente não possui e-mail cadastrado no campo 'EMAIL'.")
        
    numero_pedido = dados_pedido.get("NUMERO_PEDIDO", "")
    os_valor = dados_pedido.get("OS")
    placa = dados_pedido.get("PLACA", "")
    
    # Configurações do Servidor Hostinger (SMTP e IMAP)
    smtp_host = config_email.get("smtp_host", "smtp.hostinger.com")
    smtp_port = config_email.get("smtp_port", 465)
    imap_host = config_email.get("imap_host", "imap.hostinger.com")
    imap_port = config_email.get("imap_port", 993)
    
    remetente = config_email.get("remetente")
    senha = config_email.get("senha")
    
    if not remetente or not senha:
        raise ValueError("As chaves 'remetente' ou 'senha' não foram informadas corretamente no dicionário de configuração.")
    
    # Montagem Dinâmica de Assunto e Corpo com base na O.S. ou Pedido
    if os_valor:
        assunto = f"O.S. {os_valor} Nota(s) e boleto(s) da Rondochassis."
        referencia_texto = f"materiais e serviços prestados no veículo de placa {placa}"
    else:
        assunto = f"Pedido {numero_pedido} Nota(s) e boleto(s) da Rondochassis."
        referencia_texto = f"materiais entregues no pedido {numero_pedido}"
        
    # Organiza os detalhes dos boletos para o corpo do e-mail
    boletos_dados = dados_pedido.get("BOLETOS", [])
    detalhes_boletos_html = ""
    
    for idx, bol in enumerate(boletos_dados):
        parcela = bol.get("PARCELA", idx + 1)
        vencimento = bol.get("VENCIMENTO", "")
        venc_fmt = "/".join(vencimento.split("-")[::-1]) if "-" in vencimento else vencimento
        valor = formatar_moeda(bol.get("VALOR", 0.0))
        pix = bol.get("QRCODEPIX", "")
        
        detalhes_boletos_html += f"""
        <hr style="border: 0; border-top: 1px solid #ccc; margin: 10px 0;">
        <p><b>Parcela {parcela}:</b> Vencimento em <b>{venc_fmt}</b> — Valor: <b>R$ {valor}</b></p>
        """
        if pix:
            detalhes_boletos_html += f"""
            <p style="font-size: 11px;"><b>Pix Copia e Cole (Parcela {parcela}):</b></p>
            <p style="background-color: #f4f4f4; padding: 8px; word-break: break-all; font-family: monospace; font-size: 10px;">
                {pix}
            </p>
            """

    corpo_html = f"""
    <p>Caro cliente <b>{cliente_nome}</b>,</p>
    <p>Estou encaminhando os documentos referentes aos {referencia_texto}. O boleto inclui todos os detalhes necessários para a efetivação do pagamento, incluindo o valor total e a data de vencimento.</p>
    
    {detalhes_boletos_html}
    
    <br>
    <p>Caso haja alguma dúvida ou necessidade de esclarecimentos adicionais, estou à disposição para ajudar.</p>
    <p>Agradeço antecipadamente pela atenção e preferência!!<br>
    Esperamos trabalhar com você em breve!</p>
    <br>
    <p>Atenciosamente,<br><b>RONDOCHASSIS SERVIÇOS LTDA</b></p>
    """
    
    # Montagem da Mensagem de E-mail (Sem Cc poluindo a caixa)
    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = cliente_email
    msg['Subject'] = assunto
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid()
    
    msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))
    
    # Função auxiliar interna para anexar arquivos encontrados
    def anexar(caminho):
        if caminho:
            caminho_arquivo = Path(caminho)
            if caminho_arquivo.exists():
                with open(caminho_arquivo, "rb") as f:
                    parte = MIMEBase('application', 'octet-stream')
                    parte.set_payload(f.read())
                encoders.encode_base64(parte)
                parte.add_header('Content-Disposition', f'attachment; filename="{caminho_arquivo.name}"')
                msg.attach(parte)
                print(f"✔ Anexado: {caminho_arquivo.name}")

    # Processa os anexos mapeados pelo arquivos.py
    anexar(arquivos_encontrados.get("PEDIDO"))
    anexar(arquivos_encontrados.get("NFS_PDF"))
    anexar(arquivos_encontrados.get("NFE_PDF"))
    anexar(arquivos_encontrados.get("NFE_XML"))
    
    for boleto_path in arquivos_encontrados.get("BOLETOS", []):
        anexar(boleto_path)
        
    # 1. Envio via SMTP (Para o cliente)
    try:
        contexto = smtplib.ssl.create_default_context()
        
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=contexto, timeout=30) as server:
                server.login(remetente, senha)
                server.sendmail(remetente, [cliente_email], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.starttls(context=contexto)
                server.login(remetente, senha)
                server.sendmail(remetente, [cliente_email], msg.as_string())
                
    except Exception as e:
        raise Exception(f"Erro ao enviar e-mail via SMTP Hostinger: {str(e)}")

    # 2. Gravação limpa na pasta de Enviados (Sent) via IMAP
    try:
        with imaplib.IMAP4_SSL(imap_host, imap_port, timeout=30) as imap:
            imap.login(remetente, senha)
            
            # Tenta salvar na pasta padrão de enviados da Hostinger
            pasta_enviados = 'INBOX.Sent'
            
            # Caso o servidor utilize outro nome comum (como 'Sent' ou 'Enviados'), faz o append
            try:
                imap.append(
                    pasta_enviados, 
                    '(\\Seen)', 
                    imaplib.Time2Internaldate(time.time()), 
                    msg.as_bytes()
                )
            except Exception:
                # Fallback para a pasta "Sent" caso INBOX.Sent dê exceção no servidor
                imap.append(
                    'Sent', 
                    '(\\Seen)', 
                    imaplib.Time2Internaldate(time.time()), 
                    msg.as_bytes()
                )
    except Exception as imap_erro:
        print(f"⚠️ Aviso: E-mail enviado ao cliente, mas ocorreu um erro ao salvar na pasta de Enviados: {imap_erro}")

    return True