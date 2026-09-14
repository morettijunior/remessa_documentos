import fdb
from pathlib import Path

# --- CONFIGURAÇÕES DO BANCO FIREBIRD (TGA) ---
DB_HOST = "SERVIDOR"
DB_PORT = 3050
DB_PATH = r"c:\tga\dados\tga.fdb"
DB_USER = "SYSDBA"
DB_PASSWORD = "masterkey"


def conectar_banco():
    try:
        return fdb.connect(
            dsn=f"{DB_HOST}/{DB_PORT}:{DB_PATH}",
            user=DB_USER,
            password=DB_PASSWORD,
            charset="ISO8859_1",
        )
    except Exception as e:
        print(f"Erro ao conectar no Firebird: {e}")
        return None


def formatar_7_digitos(numero):
    """Garante o formato de 7 dígitos para busca no banco (ex: 32257 -> 0032257)"""
    if not numero:
        return ""
    return str(numero).strip().zfill(7)


def limpar_zeros(numero):
    """Remove os zeros à esquerda para nome de arquivos (ex: 0032257 -> 32257)"""
    if not numero:
        return ""
    return str(numero).strip().lstrip("0")


def consultar_pedido(numero_input):
    con = conectar_banco()
    if not con:
        return None

    cursor = con.cursor()
    num_formatado = formatar_7_digitos(numero_input)
    num_limpo = limpar_zeros(numero_input)

    try:
        # 1. Busca o movimento principal na TMOV
        query_mov = """
            SELECT IDMOV, NUMEROMOV, SERIE, IDMOVRELAC, CODCFO, OB_NUMEROSERIE 
            FROM TMOV 
            WHERE NUMEROMOV = ?
        """
        cursor.execute(query_mov, (num_formatado,))
        mov_principal = cursor.fetchone()

        if not mov_principal:
            print(f"Movimento {num_formatado} não encontrado na tabela TMOV.")
            return None

        id_mov, num_mov, serie, id_mov_relac, cod_cfo, placa = mov_principal
        eh_os = id_mov_relac is not None

        dados = {
            "NUMERO_PEDIDO": num_limpo,  # Pedido sem zeros (ex: 32257)
            "SERIE": serie.strip(),
            "ID_MOV": id_mov,
            "OS": None,
            "EV": num_limpo,
            "NFE": None,
            "CHAVEACESSO_NFE": None,
            "ANO_MES_NFE": None,
            "XML": None,  # Caminho completo do XML montado dinamicamente
            "NFS": None,
            "RPS": None,
            "PLACA": placa.strip() if placa else None,
            "CODCFO": cod_cfo.strip() if cod_cfo else None,
            "CLIENTE_NOME": None,
            "CLIENTE_DOC": None,
            # Endereço Principal (para Nota Fiscal)
            "CLIENTE_RUA": None,
            "CLIENTE_NUMERO": None,
            "CLIENTE_BAIRRO": None,
            "CLIENTE_CIDADE": None,
            "CLIENTE_ESTADO": None,
            "CLIENTE_CEP": None,
            # Endereço de Cobrança (para Boleto)
            "CLIENTE_RUAPGTO": None,
            "CLIENTE_NUMEROPGTO": None,
            "CLIENTE_BAIRROPGTO": None,
            "CLIENTE_CIDADEPGTO": None,
            "CLIENTE_ESTADOPGTO": None,
            "CLIENTE_CEPPGTO": None,
            "EMAIL": None,
            "WHATSAPP": None,
            "BOLETOS": [],
        }

        if eh_os:
            query_os = "SELECT NUMEROMOV, SERIE FROM TMOV WHERE IDMOV = ?"
            cursor.execute(query_os, (id_mov_relac,))
            os_relacionada = cursor.fetchone()
            if os_relacionada and os_relacionada[1].strip().upper() == "OS":
                dados["OS"] = limpar_zeros(os_relacionada[0])

        # 2. Varredura de Notas Filhas (NFE e NFS/RPS)
        query_filhos = """
            SELECT IDMOV, SERIE, NUMEROMOV, CHAVEACESSO, HORARIOEMISSAO 
            FROM TMOV 
            WHERE IDMOVRELAC = ?
        """
        cursor.execute(query_filhos, (id_mov,))
        filhos = cursor.fetchall()

        nfe_encontrada = None
        rps_encontrado = None

        for filho in filhos:
            f_id, f_serie, f_num, chave_tmov, data_emissao = filho
            f_serie_limpa = f_serie.strip()

            if f_serie_limpa == "1":
                nfe_encontrada = f_num.strip()
                dados["NFE"] = limpar_zeros(nfe_encontrada)

                # Busca a Chave de Acesso na tabela TNFE usando o IDMOV do filho
                query_tnfe = "SELECT CHAVEACESSO FROM TNFE WHERE IDMOV = ?"
                cursor.execute(query_tnfe, (f_id,))
                tnfe_res = cursor.fetchone()
                if tnfe_res and tnfe_res[0]:
                    dados["CHAVEACESSO_NFE"] = str(tnfe_res[0]).strip()

                # Extrai Ano e Mês da data de emissão (ex: 2026-08-20 -> 202608)
                if data_emissao:
                    data_str = str(data_emissao).split()[0]
                    partes = data_str.split("-")
                    if len(partes) >= 2:
                        dados["ANO_MES_NFE"] = f"{partes[0]}{partes[1]}"

                # Monta o caminho do XML: C:\TGA\Nfe\XML\202609\NFe\chavedeacesso-nfe.xml
                if dados["CHAVEACESSO_NFE"] and dados["ANO_MES_NFE"]:
                    pasta_base_xmls = r"C:\TGA\Nfe\XML"
                    caminho_xml_gerado = Path(pasta_base_xmls) / dados["ANO_MES_NFE"] / "NFe" / f"{dados['CHAVEACESSO_NFE']}-nfe.xml"
                    if caminho_xml_gerado.exists():
                        dados["XML"] = str(caminho_xml_gerado)

            elif f_serie_limpa.upper() == "NFS":
                rps_encontrado = f_num.strip()
                dados["RPS"] = rps_encontrado
                query_nfse = "SELECT NUMERONFSE FROM TNFEMUNICIPAL WHERE IDMOV = ?"
                cursor.execute(query_nfse, (f_id,))
                nfse_res = cursor.fetchone()
                if nfse_res:
                    dados["NFS"] = str(nfse_res[0]).strip()

        # --- BUSCA NA FLAN SEGUINDO A REGRA DE 4 ETAPAS COM VALIDAÇÃO DE BOLETO ---
        lancamentos_flan = []

        doc_pedido = num_formatado  # 1º: Pedido com 00
        nfe_com_zeros = formatar_7_digitos(nfe_encontrada) if nfe_encontrada else ""  # 2º: NFe com 00
        rps_com_zeros = formatar_7_digitos(rps_encontrado) if rps_encontrado else ""  # 3º: NFS/RPS com 00
        
        nfe_limpa_str = limpar_zeros(nfe_encontrada) if nfe_encontrada else ""
        nfs_limpa_str = str(dados["NFS"]).strip() if dados.get("NFS") else ""
        doc_manual_unificado = (
            f"{nfe_limpa_str}/{nfs_limpa_str}"
            if (nfe_limpa_str and nfs_limpa_str)
            else ""
        )  # 4º: Manual NFE/NFS limpo

        def consultar_flan_com_boleto(doc):
            """Consulta a FLAN usando TRIM para garantir o match e valida se possui dados de boleto/PIX."""
            if not doc:
                return []
            
            doc_limpo = str(doc).strip()
            q = """
                SELECT PARCELA, CODCFO, NUMERODOCUMENTO, DATAVENCIMENTO, VALORORIGINAL, CODBARRABOLETO, LINHADIGITAVELBOLETO, QRCODEPIX, BOL_NUMERO 
                FROM FLAN 
                WHERE TRIM(NUMERODOCUMENTO) = ? 
                ORDER BY PARCELA
            """
            cursor.execute(q, (doc_limpo,))
            rows = cursor.fetchall()

            if not rows:
                return []

            # Valida se pelo menos um registro possui dados reais de boleto ou PIX preenchidos
            tem_dados_cobranca = any(
                (r[5] and str(r[5]).strip() and str(r[5]).strip() != "None")
                or (r[6] and str(r[6]).strip() and str(r[6]).strip() != "None")
                or (r[7] and str(r[7]).strip() and str(r[7]).strip() != "None")
                for r in rows
            )

            return rows if tem_dados_cobranca else []

        # 1ª ETAPA: Numero do pedido
        lancamentos_flan = consultar_flan_com_boleto(doc_pedido)

        # 2ª ETAPA: NFe lançada pelo sistema
        if not lancamentos_flan:
            lancamentos_flan = consultar_flan_com_boleto(nfe_com_zeros)

        # 3ª ETAPA: NFS lançada pelo sistema (RPS)
        if not lancamentos_flan:
            lancamentos_flan = consultar_flan_com_boleto(rps_com_zeros)

        # 4ª ETAPA: NFE/NFS manual unificado
        if not lancamentos_flan:
            lancamentos_flan = consultar_flan_com_boleto(doc_manual_unificado)

        # Processa os lançamentos encontrados na etapa vencedora
        dados["BOLETOS"] = []
        vistos = set()

        for flan in lancamentos_flan:
            parcela, cfo_flan, num_doc, dt_venc, val_orig, cod_barras, linha_dig, pix, bol_num = flan
            if cfo_flan and not dados["CODCFO"]:
                dados["CODCFO"] = cfo_flan.strip()

            num_doc_limpo = num_doc.strip() if num_doc else ""
            chave_unica = (parcela, num_doc_limpo)

            if chave_unica not in vistos:
                vistos.add(chave_unica)
                dados["BOLETOS"].append({
                    "PARCELA": parcela,
                    "NUMERO_DOCUMENTO": num_doc_limpo,
                    "VENCIMENTO": str(dt_venc) if dt_venc else None,
                    "VALOR": float(val_orig) if val_orig else 0.0,
                    "BOL_NUMERO": bol_num.strip() if (bol_num and str(bol_num).strip() != "None") else None,
                    "CODBARRABOLETO": cod_barras.strip() if (cod_barras and str(cod_barras).strip() != "None") else None,
                    "LINHADIGITAVELBOLETO": linha_dig.strip() if (linha_dig and str(linha_dig).strip() != "None") else None,
                    "QRCODEPIX": pix.strip() if (pix and str(pix).strip() != "None") else None,
                })

        # 4. Buscar dados completos do cliente na FCFO (Nota vs. Cobrança)
        if dados["CODCFO"]:
            query_fcfo = """
                SELECT NOME, EMAIL, FAX, CGCCFO, 
                       RUA, NUMERO, BAIRRO, CIDADE, CODETD, CEP, 
                       RUAPGTO, NUMEROPGTO, BAIRROPGTO, CIDADEPGTO, CODETDPGTO, CEPPGTO 
                FROM FCFO 
                WHERE CODCFO = ?
            """
            cursor.execute(query_fcfo, (dados["CODCFO"],))
            cliente = cursor.fetchone()
            if cliente:
                dados["CLIENTE_NOME"] = cliente[0].strip() if cliente[0] else None
                dados["EMAIL"] = cliente[1].strip() if cliente[1] else None
                dados["WHATSAPP"] = cliente[2].strip() if cliente[2] else None
                dados["CLIENTE_DOC"] = cliente[3].strip() if cliente[3] else None
                
                # Endereço Principal (Nota)
                dados["CLIENTE_RUA"] = cliente[4].strip() if cliente[4] else None
                dados["CLIENTE_NUMERO"] = cliente[5].strip() if cliente[5] else None
                dados["CLIENTE_BAIRRO"] = cliente[6].strip() if cliente[6] else None
                dados["CLIENTE_CIDADE"] = cliente[7].strip() if cliente[7] else None
                dados["CLIENTE_ESTADO"] = cliente[8].strip() if cliente[8] else None
                dados["CLIENTE_CEP"] = cliente[9].strip() if cliente[9] else None

                # Endereço de Cobrança (Boleto)
                dados["CLIENTE_RUAPGTO"] = cliente[10].strip() if cliente[10] else None
                dados["CLIENTE_NUMEROPGTO"] = cliente[11].strip() if cliente[11] else None
                dados["CLIENTE_BAIRROPGTO"] = cliente[12].strip() if cliente[12] else None
                dados["CLIENTE_CIDADEPGTO"] = cliente[13].strip() if cliente[13] else None
                dados["CLIENTE_ESTADOPGTO"] = cliente[14].strip() if cliente[14] else None
                dados["CLIENTE_CEPPGTO"] = cliente[15].strip() if cliente[15] else None

        return dados

    except Exception as e:
        print(f"Erro ao processar consulta no BD para o pedido {numero_input}: {e}")
        return None
    finally:
        con.close()