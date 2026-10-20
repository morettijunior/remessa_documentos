import smtplib
import imaplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.encoders import encode_base64
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
    e grava uma cópia diretamente na pasta 'Sent' (Enviados) via IMAP,
    com formatação de texto e assunto 100% dinâmica baseada nos arquivos anexados.
    """
    cliente_nome = dados_pedido.get("CLIENTE_NOME", "Cliente")
    email_raw = dados_pedido.get("EMAIL")
    
    if not email_raw:
        raise ValueError("O cliente não possui e-mail cadastrado no campo 'EMAIL'.")
        
    email_tratado = str(email_raw).replace(";", ",")
    destinatarios = [e.strip() for e in email_tratado.split(",") if e.strip()]
    
    if not destinatarios:
        raise ValueError("Nenhum e-mail válido foi encontrado no cadastro do cliente.")

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
    assinatura_path = config_email.get("assinatura_path")
    
    if not remetente or not senha:
        raise ValueError("As chaves 'remetente' ou 'senha' não foram informadas corretamente no dicionário de configuração.")
    
    # Verificação dos arquivos que realmente existem
    tem_pedido = bool(arquivos_encontrados.get("PEDIDO") and Path(arquivos_encontrados.get("PEDIDO")).exists())
    tem_nfs = bool(arquivos_encontrados.get("NFS_PDF") and Path(arquivos_encontrados.get("NFS_PDF")).exists())
    tem_nfe_pdf = bool(arquivos_encontrados.get("NFE_PDF") and Path(arquivos_encontrados.get("NFE_PDF")).exists())
    tem_nfe_xml = bool(arquivos_encontrados.get("NFE_XML") and Path(arquivos_encontrados.get("NFE_XML")).exists())
    
    lista_boletos_anexos = arquivos_encontrados.get("BOLETOS", [])
    tem_boletos = any(Path(b).exists() for b in lista_boletos_anexos if b)
    qtd_boletos = len([b for b in lista_boletos_anexos if b and Path(b).exists()])

    # Conta quantas notas (PDFs) existem
    qtd_notas = 0
    if tem_nfs:
        qtd_notas += 1
    if tem_nfe_pdf:
        qtd_notas += 1

    # --- MONTAGEM DINÂMICA DE PARTES DO ASSUNTO E TEXTO ---
    partes_doc = []
    if qtd_notas > 0:
        partes_doc.append("Nota(s) Fiscal(is)")
    if tem_pedido:
        partes_doc.append(f"Pedido {numero_pedido}")
    
    termo_docs_assunto = " e ".join(partes_doc) if partes_doc else f"Pedido {numero_pedido}"
    termo_boleto_assunto = "Boletos" if qtd_boletos > 1 else "Boleto"

    if os_valor:
        assunto = f"O.S. {os_valor} — {termo_docs_assunto} e {termo_boleto_assunto} da Rondochassis."
        referencia_texto = f"materiais e serviços prestados no veículo de placa {placa} (O.S. {os_valor})"
    else:
        assunto = f"{termo_docs_assunto} e {termo_boleto_assunto} da Rondochassis."
        referencia_texto = f"materiais entregues no pedido {numero_pedido}"

    termo_boleto_texto = "Os boletos incluem" if qtd_boletos > 1 else "O boleto inclui"

    # Organiza os detalhes dos boletos para o corpo do e-mail
    boletos_dados = dados_pedido.get("BOLETOS", [])
    detalhes_boletos_html = ""
    
    for idx, bol in enumerate(boletos_dados, start=1):
        vencimento = bol.get("VENCIMENTO", "")
        venc_fmt = "/".join(vencimento.split("-")[::-1]) if "-" in vencimento else vencimento
        valor = formatar_moeda(bol.get("VALOR", 0.0))
        
        detalhes_boletos_html += f"Parcela {idx}: Vencimento em {venc_fmt} — Valor: R$ {valor}<br>\n"

    # Montagem da listagem de arquivos HTML
    lista_arquivos_html = ""
    if tem_pedido:
        lista_arquivos_html += "<li>Cópia do Pedido</li>\n"
    if tem_nfs:
        lista_arquivos_html += "<li>Nota Fiscal de Serviços (pdf)</li>\n"
    if tem_nfe_pdf:
        lista_arquivos_html += "<li>Nota Fiscal de Peças (pdf)</li>\n"
    if tem_nfe_xml:
        lista_arquivos_html += "<li>Nota Fiscal de Peças (xml)</li>\n"
    if tem_boletos:
        lista_arquivos_html += f"<li>Boleto(s) ({qtd_boletos} parcela(s))</li>\n"

    # Montagem do HTML principal do e-mail
    corpo_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333333; font-size: 14px; line-height: 1.5;">
        <p>Caro cliente <b>{cliente_nome}</b>,</p>
        <p>Estou encaminhando os documentos referentes aos {referencia_texto}. {termo_boleto_texto} todos os detalhes necessários para a efetivação do pagamento, incluindo o valor total e a data de vencimento.</p>
        
        <p>
        {detalhes_boletos_html}
        </p>
        
        <p>Em anexo neste email seguem os seguintes arquivos:</p>
        <ul>
            {lista_arquivos_html}
        </ul>
        
        <p>Caso haja alguma dúvida ou necessidade de esclarecimentos adicionais, estou à disposição para ajudar.<br>
        Agradeço antecipadamente pela atenção e preferência!!<br>
        Esperamos trabalhar com você em breve!</p>
        
        <p>Atenciosamente,<br><b>RONDOCHASSIS SERVIÇOS LTDA</b></p>
    """

    if assinatura_path and Path(assinatura_path).exists():
        corpo_html += '<br><img src="cid:assinatura_imagem" alt="Assinatura" style="max-width: 750px; height: auto;"><br>'

    corpo_html += """
    </body>
    </html>
    """
    
    # Montagem da Mensagem de E-mail
    msg = MIMEMultipart('related')
    msg['From'] = remetente
    msg['To'] = ", ".join(destinatarios)
    msg['Subject'] = assunto
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid()
    
    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)
    
    msg_alternative.attach(MIMEText(corpo_html, 'html', 'utf-8'))
    
    if assinatura_path and Path(assinatura_path).exists():
        try:
            with open(assinatura_path, "rb") as f:
                img_data = f.read()
                img = MIMEImage(img_data)
                img.add_header('Content-ID', '<assinatura_imagem>')
                img.add_header('Content-Disposition', 'inline', filename=Path(assinatura_path).name)
                msg.attach(img)
        except Exception as e:
            print(f"⚠️ Aviso: Não foi possível anexar a imagem de assinatura: {e}")

    def anexar(caminho):
        if caminho:
            caminho_arquivo = Path(caminho)
            if caminho_arquivo.exists():
                with open(caminho_arquivo, "rb") as f:
                    parte = MIMEBase('application', 'octet-stream')
                    parte.set_payload(f.read())
                encode_base64(parte)
                parte.add_header('Content-Disposition', f'attachment; filename="{caminho_arquivo.name}"')
                msg.attach(parte)
                print(f"✔ Anexado: {caminho_arquivo.name}")

    anexar(arquivos_encontrados.get("PEDIDO"))
    anexar(arquivos_encontrados.get("NFS_PDF"))
    anexar(arquivos_encontrados.get("NFE_PDF"))
    anexar(arquivos_encontrados.get("NFE_XML"))
    
    for boleto_path in lista_boletos_anexos:
        anexar(boleto_path)
        
    # 1. Envio via SMTP
    try:
        contexto = smtplib.ssl.create_default_context()
        
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=contexto, timeout=30) as server:
                server.login(remetente, senha)
                server.sendmail(remetente, destinatarios, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.starttls(context=contexto)
                server.login(remetente, senha)
                server.sendmail(remetente, destinatarios, msg.as_string())
                
    except Exception as e:
        raise Exception(f"Erro ao enviar e-mail via SMTP Hostinger: {str(e)}")

    # 2. Gravação na pasta de Enviados via IMAP
    try:
        with imaplib.IMAP4_SSL(imap_host, imap_port, timeout=30) as imap:
            imap.login(remetente, senha)
            
            pasta_enviados = 'INBOX.Sent'
            try:
                imap.append(
                    pasta_enviados, 
                    '(\\Seen)', 
                    imaplib.Time2Internaldate(time.time()), 
                    msg.as_bytes()
                )
            except Exception:
                imap.append(
                    'Sent', 
                    '(\\Seen)', 
                    imaplib.Time2Internaldate(time.time()), 
                    msg.as_bytes()
                )
    except Exception as imap_erro:
        print(f"⚠️ Aviso: E-mail enviado aos destinatários, mas ocorreu um erro ao salvar na pasta de Enviados: {imap_erro}")

    return True