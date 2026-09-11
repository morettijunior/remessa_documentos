from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def gerar_pdf_boleto(dados_pedido, pasta_destino):
    caminho_saida = Path(pasta_destino)
    caminho_saida.mkdir(parents=True, exist_ok=True)
    
    arquivos_gerados = []
    
    beneficiario_nome = "RONDOCHASSIS SERVIÇOS LTDA - EPP - CNPJ: 04.805.977/0001-37"
    agencia_codigo = "4349/1626-8"
    
    cliente_nome = dados_pedido.get("CLIENTE_NOME", "CLIENTE NÃO IDENTIFICADO")
    
    for boleto in dados_pedido.get("BOLETOS", []):
        parcela = boleto.get("PARCELA", 1)
        num_doc = boleto.get("NUMERO_DOCUMENTO", "DOC")
        vencimento = boleto.get("VENCIMENTO", "")
        valor = boleto.get("VALOR", 0.0)
        bol_numero = boleto.get("BOL_NUMERO", "")
        
        nome_arquivo = f"Boleto_{dados_pedido['NUMERO_PEDIDO']}_P{parcela}.pdf"
        caminho_arquivo = caminho_saida / nome_arquivo
        
        doc = SimpleDocTemplate(
            str(caminho_arquivo),
            pagesize=letter,
            rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        style_lbl = ParagraphStyle('Lbl', parent=styles['Normal'], fontSize=5.5, leading=6.5, textColor=colors.black)
        style_val = ParagraphStyle('Val', parent=styles['Normal'], fontSize=7.5, leading=9, fontName='Helvetica-Bold')
        style_banco_cod = ParagraphStyle('BnkCod', parent=styles['Normal'], fontSize=12, leading=14, fontName='Helvetica-Bold', alignment=1)
        style_pontilhado = ParagraphStyle('Pont', parent=styles['Normal'], fontSize=6, leading=7, alignment=1, textColor=colors.HexColor('#666666'))
        
        venc_fmt = "/".join(vencimento.split("-")[::-1]) if "-" in vencimento else vencimento

        try:
            logo_banco = Image("756.bmp", width=60, height=15)
        except Exception:
            logo_banco = Paragraph("<b>SICOOB</b>", style_val)

        comp_data = [
            [
                logo_banco, 
                Paragraph("<b>756-0</b>", style_banco_cod), 
                Paragraph("<b>Comprovante de Entrega</b>", ParagraphStyle('Tit', parent=style_val, fontSize=9)), 
                "", "", ""
            ],
            [
                Paragraph(f"Beneficiário<br/><b>{beneficiario_nome}</b>", style_lbl), 
                "", 
                Paragraph(f"Agencia / Codigo Beneficiário<br/><b>{agencia_codigo}</b>", style_lbl), 
                Paragraph("Motivo de nao entrega. (Para uso da empresa entregadora)", style_lbl), "", ""
            ],
            [
                Paragraph(f"Pagador<br/><b>{cliente_nome}</b>", style_lbl), 
                "", 
                Paragraph(f"Nosso Número<br/><b>{bol_numero}</b>", style_lbl), 
                Paragraph("[  ] Mudou-se", style_lbl), 
                Paragraph("[  ] Ausente", style_lbl), 
                Paragraph("[  ] Não existe nº. indicado", style_lbl)
            ],
            [
                Paragraph(f"Vencimento<br/><b>{venc_fmt}</b>", style_lbl), 
                Paragraph(f"Número do Documento<br/><b>{num_doc}</b>", style_lbl), 
                Paragraph(f"Espécie<br/><b>R$</b>", style_lbl), 
                Paragraph(f"Valor do Documento<br/><b>{valor:,.2f}</b>", style_lbl), 
                Paragraph("[  ] Recusado", style_lbl), 
                Paragraph("[  ] Endereço insuficiente", style_lbl)
            ],
            [
                Paragraph("Recebemos o Titulo<br/>com as características acima", style_lbl), 
                Paragraph("Data<br/>____/____/________", style_lbl), 
                Paragraph("Assinatura<br/>____________________", style_lbl), 
                Paragraph("Data<br/>____/____/________", style_lbl), 
                Paragraph("Assinatura<br/>____________________", style_lbl), 
                Paragraph("[  ] Desconhecido<br/>[  ] Outros (anotar no verso)", style_lbl)
            ],
            [
                Paragraph("Local de Pagamento<br/><b>Pagavel em qualquer Banco</b>", style_lbl), 
                "", "", "", 
                Paragraph("Data do Processamento<br/><b>11/09/2026</b>", style_lbl), 
                ""
            ]
        ]
        
        # Ajustado colWidths para dar espaço suficiente na coluna do 756-0 (50pt)
        tabela_comp = Table(comp_data, colWidths=[70, 50, 120, 95, 95, 146])
        tabela_comp.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 2.5),
            ('SPAN', (2,0), (5,0)),
            ('SPAN', (0,1), (1,1)), 
            ('SPAN', (3,1), (5,1)), 
            ('SPAN', (0,2), (1,2)), 
            ('SPAN', (4,3), (5,3)), 
            ('SPAN', (0,5), (3,5)), 
            ('SPAN', (4,5), (5,5)), 
        ]))
        
        story.append(tabela_comp)
        story.append(Spacer(1, 4))
        story.append(Paragraph("- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -", style_pontilhado))
        
        doc.build(story)
        arquivos_gerados.append(str(caminho_arquivo))
        
    return arquivos_gerados