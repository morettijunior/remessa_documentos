from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.barcode import code128
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing

def formatar_moeda(valor):
    """Formata float para o padrão monetário brasileiro (ex: 1.0 -> 1,00 ou 1500.5 -> 1.500,50)"""
    if not valor:
        return "0,00"
    val_str = f"{float(valor):,.2f}"
    val_str = val_str.replace(",", "X").replace(".", ",").replace("X", ".")
    return val_str

def formatar_linha_digitavel(linha):
    """Formata a linha digitável adicionando os pontos nos blocos padrão"""
    if not linha:
        return ""
    nums = "".join([c for c in linha if c.isdigit()])
    if len(nums) == 47:
        b1 = f"{nums[0:5]}.{nums[5:10]}"
        b2 = f"{nums[10:15]}.{nums[15:21]}"
        b3 = f"{nums[21:26]}.{nums[26:32]}"
        b4 = f"{nums[32]}"
        b5 = f"{nums[33:47]}"
        return f"{b1} {b2} {b3} {b4} {b5}"
    return linha

def gerar_pdf_boleto(dados_pedido, pasta_destino):
    caminho_saida = Path(pasta_destino)
    caminho_saida.mkdir(parents=True, exist_ok=True)
    
    arquivos_gerados = []
    
    beneficiario_nome = "RONDOCHASSIS SERVIÇOS LTDA - EPP - CNPJ: 04.805.977/0001-37"
    beneficiario_end = "AV. DAS PERDIZES, 2615 JARDIM DAS PAINEIRAS, RONDONOPOLIS/MT 78745000 Fone: 6634210400"
    agencia_codigo = "4349/1626-8"
    
    cliente_nome = dados_pedido.get("CLIENTE_NOME", "CLIENTE NÃO IDENTIFICADO")
    cliente_doc = dados_pedido.get("CLIENTE_DOC", "")
    
    # Endereço de cobrança (com fallback para o principal)
    rua = dados_pedido.get("CLIENTE_RUAPGTO") or dados_pedido.get("CLIENTE_RUA") or ""
    num = dados_pedido.get("CLIENTE_NUMEROPGTO") or dados_pedido.get("CLIENTE_NUMERO") or ""
    bairro = dados_pedido.get("CLIENTE_BAIRROPGTO") or dados_pedido.get("CLIENTE_BAIRRO") or ""
    cidade = dados_pedido.get("CLIENTE_CIDADEPGTO") or dados_pedido.get("CLIENTE_CIDADE") or ""
    uf = dados_pedido.get("CLIENTE_ESTADOPGTO") or dados_pedido.get("CLIENTE_ESTADO") or ""
    cep = dados_pedido.get("CLIENTE_CEPPGTO") or dados_pedido.get("CLIENTE_CEP") or ""
    endereco_completo = f"{rua} {num} - {bairro}, {cidade} / {uf} - {cep}"
    
    for boleto in dados_pedido.get("BOLETOS", []):
        parcela = boleto.get("PARCELA", 1)
        num_doc = boleto.get("NUMERO_DOCUMENTO", "DOC")
        vencimento = boleto.get("VENCIMENTO", "")
        valor_bruto = boleto.get("VALOR", 0.0)
        valor_fmt = formatar_moeda(valor_bruto)
        
        bol_numero = boleto.get("BOL_NUMERO", "")
        linha_dig = boleto.get("LINHADIGITAVELBOLETO", "")
        pix = boleto.get("QRCODEPIX", "")
        
        nome_arquivo = f"Boleto_{dados_pedido['NUMERO_PEDIDO']}_P{parcela}.pdf"
        caminho_arquivo = caminho_saida / nome_arquivo
        
        doc = SimpleDocTemplate(
            str(caminho_arquivo),
            pagesize=letter,
            rightMargin=14, leftMargin=14, topMargin=12, bottomMargin=12
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        style_lbl = ParagraphStyle('Lbl', parent=styles['Normal'], fontSize=7.5, leading=8.5, textColor=colors.black)
        style_val = ParagraphStyle('Val', parent=styles['Normal'], fontSize=9.5, leading=11, fontName='Helvetica-Bold')
        style_banco_cod = ParagraphStyle('BnkCod', parent=styles['Normal'], fontSize=14, leading=16, fontName='Helvetica-Bold', alignment=1)
        style_linha_dig = ParagraphStyle('LDig', parent=styles['Normal'], fontSize=11, leading=13, fontName='Helvetica-Bold', alignment=2)
        style_pontilhado = ParagraphStyle('Pont', parent=styles['Normal'], fontSize=5, leading=5.5, alignment=1, textColor=colors.HexColor('#666666'))
        
        venc_fmt = "/".join(vencimento.split("-")[::-1]) if "-" in vencimento else vencimento
        linha_dig_formatada = formatar_linha_digitavel(linha_dig)

        try:
            logo_banco = Image("756.bmp", width=60, height=15)
        except Exception:
            logo_banco = Paragraph("<b>SICOOB</b>", style_val)

        # -------------------------------------------------------------
        # 1. COMPROVANTE DE ENTREGA 
        # -------------------------------------------------------------
        comp_data = [
            [
                logo_banco, 
                Paragraph("<b>756-0</b>", style_banco_cod), 
                Paragraph("<b>Comprovante de Entrega</b>", ParagraphStyle('Tit', parent=style_val, fontSize=11)), 
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
                Paragraph(f"Número do Doc<br/><b>{num_doc}</b>", style_lbl), 
                Paragraph(f"Espécie<br/><b>R$</b>", style_lbl), 
                Paragraph(f"Valor do Documento<br/><b>{valor_fmt}</b>", style_lbl), 
                Paragraph("[  ] Recusado", style_lbl), 
                Paragraph("[  ] Endereço insuficiente", style_lbl)
            ],
            [
                Paragraph("Recebemos o Titulo<br/>com as características acima", style_lbl), 
                Paragraph("Data<br/>___/___/___", style_lbl), 
                Paragraph("Assinatura<br/>____________________", style_lbl), 
                Paragraph("Data<br/>____/____/______", style_lbl), 
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
        
        tabela_comp = Table(comp_data, colWidths=[70, 65, 105, 95, 95, 156])
        tabela_comp.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 1.5),
            ('SPAN', (2,0), (5,0)),
            ('SPAN', (0,1), (1,1)), 
            ('SPAN', (3,1), (5,1)), 
            ('SPAN', (0,2), (1,2)), 
            ('SPAN', (4,3), (5,3)), 
            ('SPAN', (0,5), (3,5)), 
            ('SPAN', (4,5), (5,5)), 
        ]))
        story.append(tabela_comp)
        story.append(Spacer(1, 1.5))
        story.append(Paragraph("- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -", style_pontilhado))
        story.append(Spacer(1, 1.5))

        # -------------------------------------------------------------
        # 2. RECIBO DO PAGADOR
        # -------------------------------------------------------------
        recibo_data = [
            [
                logo_banco, 
                Paragraph("<b>756-0</b>", style_banco_cod), 
                Paragraph("<b>Recibo do Pagador</b>", ParagraphStyle('TitR', parent=style_val, fontSize=11)), 
                "", "", ""
            ],
            [
                Paragraph("Local de Pagamento<br/><b>Pagavel em qualquer Banco</b>", style_lbl), 
                "", "", 
                Paragraph(f"Vencimento<br/><b>{venc_fmt}</b>", style_lbl), 
                "", ""
            ],
            [
                Paragraph(f"Beneficiário<br/><b>{beneficiario_nome}</b><br/>{beneficiario_end}", style_lbl), 
                "", "", 
                Paragraph(f"Agência / Código Beneficiário<br/><b>{agencia_codigo}</b>", style_lbl), 
                "", ""
            ],
            [
                Paragraph("Data do Documento<br/><b>11/09/2026</b>", style_lbl),
                Paragraph(f"Numero do Doc<br/><b>{num_doc}</b>", style_lbl),
                Paragraph("Especie Doc.<br/><b>DM</b>", style_lbl),
                Paragraph("Aceite<br/><b>N</b>", style_lbl),
                Paragraph("Data do Processamento<br/><b>11/09/2026</b>", style_lbl),
                Paragraph(f"Nosso Número<br/><b>{bol_numero}</b>", style_lbl)
            ],
            [
                Paragraph("Uso do Banco<br/><b></b>", style_lbl),
                Paragraph("Carteira<br/><b>1</b>", style_lbl),
                Paragraph("Especie<br/><b>R$</b>", style_lbl),
                Paragraph("Quantidade<br/><b></b>", style_lbl),
                Paragraph("Valor<br/><b></b>", style_lbl),
                Paragraph(f"(=) Valor do Documento<br/><b>{valor_fmt}</b>", style_lbl)
            ],
            [
                Paragraph(
                    "Instruções (Texto de responsabilidade do beneficiário.)<br/>"
                    "TESTE — APOS O VENC. COBRAR MULTA DE 2,00% | JUROS DE 0,17% DIA<br/>"
                    f"Parcela {parcela} de 1 &nbsp;|&nbsp; Pix Copia e Cole: <font size=5>{pix}</font>",
                    style_lbl
                ),
                "", "", "", "",
                Paragraph("(-) Desconto<br/><b></b>", style_lbl)
            ],
            [
                "", "", "", "", "",
                Paragraph("(-) Outras Deducoes / Abatimento<br/><b></b>", style_lbl)
            ],
            [
                "", "", "", "", "",
                Paragraph("(+) Mora / Multa / Juros<br/><b></b>", style_lbl)
            ],
            [
                "", "", "", "", "",
                Paragraph("(+) Outros Acrescimos<br/><b></b>", style_lbl)
            ],
            [
                "", "", "", "", "",
                Paragraph("(=) Valor Cobrado<br/><b></b>", style_lbl)
            ],
            [
                Paragraph(f"Pagador: <b>{cliente_nome}</b> &nbsp;|&nbsp; {endereco_completo}", style_lbl),
                "", "", "",
                Paragraph(f"CPF / CNPJ<br/><b>{cliente_doc}</b>", style_lbl),
                ""
            ],
            [
                Paragraph("Beneficiário Final:", style_lbl),
                "", "", "",
                Paragraph("Código de Baixa<br/><b></b>", style_lbl),
                ""
            ]
        ]
        
        tabela_recibo = Table(recibo_data, colWidths=[70, 65, 105, 95, 95, 156])
        tabela_recibo.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 1.5),
            ('SPAN', (2,0), (5,0)),
            ('SPAN', (0,1), (2,1)), ('SPAN', (3,1), (5,1)),
            ('SPAN', (0,2), (2,2)), ('SPAN', (3,2), (5,2)),
            ('SPAN', (0,5), (4,9)),
            ('SPAN', (0,10), (3,10)), ('SPAN', (4,10), (5,10)),
            ('SPAN', (0,11), (3,11)), ('SPAN', (4,11), (5,11)),
        ]))
        story.append(tabela_recibo)
        story.append(Spacer(1, 1.5))
        story.append(Paragraph("- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -", style_pontilhado))
        story.append(Spacer(1, 1.5))

        # -------------------------------------------------------------
        # 3. FICHA DE COMPENSAÇÃO
        # -------------------------------------------------------------
        qr_drawing = None
        if pix:
            try:
                qr = QrCodeWidget(pix)
                bounds = qr.getBounds()
                w = bounds[2] - bounds[0]
                h = bounds[3] - bounds[1]
                qr_drawing = Drawing(55, 55, transform=[55/w, 0, 0, 55/h, 0, 0])
                qr_drawing.add(qr)
            except Exception:
                qr_drawing = Paragraph("[QR CODE]", style_lbl)

        ficha_data = [
            [
                logo_banco, 
                Paragraph("<b>756-0</b>", style_banco_cod), 
                Paragraph(linha_dig_formatada if linha_dig_formatada else "", style_linha_dig), 
                "", "", ""
            ],
            [
                Paragraph("Local de Pagamento<br/><b>Pagavel em qualquer Banco</b>", style_lbl), 
                "", "", 
                Paragraph(f"Vencimento<br/><b>{venc_fmt}</b>", style_lbl), 
                "", ""
            ],
            [
                Paragraph(f"Beneficiário<br/><b>{beneficiario_nome}</b><br/>{beneficiario_end}", style_lbl), 
                "", "", 
                Paragraph(f"Agencia / Codigo Beneficiário<br/><b>{agencia_codigo}</b>", style_lbl), 
                "", ""
            ],
            [
                Paragraph("Data do Documento<br/><b>11/09/2026</b>", style_lbl), 
                Paragraph(f"Número do Doc<br/><b>{num_doc}</b>", style_lbl), 
                Paragraph("Espécie Doc.<br/><b>DM</b>", style_lbl), 
                Paragraph("Aceite<br/><b>N</b>", style_lbl), 
                Paragraph("Data do Processamento<br/><b>11/09/2026</b>", style_lbl), 
                Paragraph(f"Nosso Número<br/><b>{bol_numero}</b>", style_lbl)
            ],
            [
                Paragraph("Uso do Banco<br/><b></b>", style_lbl), 
                Paragraph("Carteira<br/><b>1</b>", style_lbl), 
                Paragraph("Espécie Moeda<br/><b>R$</b>", style_lbl), 
                Paragraph("Quantidade<br/><b></b>", style_lbl), 
                Paragraph("Valor<br/><b></b>", style_lbl), 
                Paragraph(f"(=) Valor do Documento<br/><b>{valor_fmt}</b>", style_lbl)
            ],
            [
                Paragraph(
                    "Instruções (Texto de responsabilidade do beneficiário.)<br/>"
                    "TESTE — APOS O VENC. COBRAR MULTA DE 2,00% | JUROS DE 0,17% DIA<br/>"
                    f"Parcela {parcela} de 1 &nbsp;|&nbsp; Pix Copia e Cole: <font size=5>{pix}</font>",
                    style_lbl
                ),
                "", "", "",
                qr_drawing if qr_drawing else "",
                Paragraph("(-) Desconto<br/><b></b>", style_lbl)
            ],
            [
                "", "", "", "", "",
                Paragraph("(-) Outras Deducoes / Abatimento<br/><b></b>", style_lbl)
            ],
            [
                "", "", "", "", "",
                Paragraph("(+) Mora / Multa / Juros<br/><b></b>", style_lbl)
            ],
            [
                "", "", "", "", "",
                Paragraph("(+) Outros Acrescimos<br/><b></b>", style_lbl)
            ],
            [
                "", "", "", "", "",
                Paragraph("(=) Valor Cobrado<br/><b></b>", style_lbl)
            ],
            [
                Paragraph(f"Pagador &nbsp;&nbsp;&nbsp;&nbsp; <b>{cliente_nome}</b> &nbsp;|&nbsp; {endereco_completo}", style_lbl),
                "", "", "",
                Paragraph(f"CPF / CNPJ<br/><b>{cliente_doc}</b>", style_lbl),
                ""
            ],
            [
                Paragraph("Beneficiário Final:", style_lbl),
                "", "", "",
                Paragraph("Código de Baixa<br/><b></b>", style_lbl),
                ""
            ]
        ]
        
        tabela_ficha = Table(ficha_data, colWidths=[70, 65, 105, 95, 95, 156])
        tabela_ficha.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 1.5),
            ('SPAN', (2,0), (5,0)),
            ('SPAN', (0,1), (2,1)), ('SPAN', (3,1), (5,1)),
            ('SPAN', (0,2), (2,2)), ('SPAN', (3,2), (5,2)),
            ('SPAN', (0,5), (3,9)),
            ('SPAN', (4,5), (4,9)),
            ('SPAN', (0,10), (3,10)), ('SPAN', (4,10), (5,10)),
            ('SPAN', (0,11), (3,11)), ('SPAN', (4,11), (5,11)),
        ]))
        story.append(tabela_ficha)
        story.append(Spacer(1, 2))

        if linha_dig:
            try:
                nums_limpos = "".join([c for c in linha_dig if c.isdigit()])
                if len(nums_limpos) == 47:
                    codigo_barras_44 = (
                        nums_limpos[0:3]
                        + nums_limpos[3:4]
                        + nums_limpos[32:33]
                        + nums_limpos[33:37]
                        + nums_limpos[37:47]
                        + nums_limpos[4:9]
                        + nums_limpos[10:20]
                        + nums_limpos[21:31]
                    )
                else:
                    codigo_barras_44 = nums_limpos[:44]

                if len(codigo_barras_44) == 44:
                    barcode = code128.Code128(codigo_barras_44, barWidth=1.3, barHeight=30)
                    story.append(barcode)
                    story.append(Spacer(1, 1))
            except Exception:
                pass

        doc.build(story)
        arquivos_gerados.append(str(caminho_arquivo))
        
    return arquivos_gerados