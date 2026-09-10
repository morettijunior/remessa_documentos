import fdb

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
        "NFS": None,
        "RPS": None,
        "PLACA": placa.strip() if placa else None,
        "CODCFO": cod_cfo.strip() if cod_cfo else None,
        "CLIENTE_NOME": None,
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

    # 2. Varredura de Notas Filhas (NFE com Chave e Data, e NFS/RPS)
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
      f_id, f_serie, f_num, chave, data_emissao = filho
      f_serie_limpa = f_serie.strip()

      if f_serie_limpa == "1":
        nfe_encontrada = f_num.strip()
        dados["NFE"] = limpar_zeros(nfe_encontrada)
        dados["CHAVEACESSO_NFE"] = chave.strip() if chave else None

        # Extrai Ano e Mês da data de emissão (ex: 2026-08-20 -> 202608)
        if data_emissao:
          data_str = str(data_emissao).split()[
              0
          ]  # Pega a parte da data YYYY-MM-DD
          partes = data_str.split("-")
          if len(partes) >= 2:
            dados["ANO_MES_NFE"] = f"{partes[0]}{partes[1]}"

      elif f_serie_limpa.upper() == "NFS":
        rps_encontrado = f_num.strip()
        dados["RPS"] = rps_encontrado
        query_nfse = "SELECT NUMERONFSE FROM TNFEMUNICIPAL WHERE IDMOV = ?"
        cursor.execute(query_nfse, (f_id,))
        nfse_res = cursor.fetchone()
        if nfse_res:
          dados["NFS"] = str(nfse_res[0]).strip()

    # 3. Consulta na FLAN para boletos
    query_flan = """
            SELECT CODCFO, NUMERODOCUMENTO, CODBARRABOLETO, LINHADIGITAVELBOLETO, QRCODEPIX 
            FROM FLAN 
            WHERE IDMOV = ?
        """
    cursor.execute(query_flan, (id_mov,))
    lancamentos_flan = cursor.fetchall()

    for flan in lancamentos_flan:
      cfo_flan, num_doc, cod_barras, linha_dig, pix = flan
      if cfo_flan and not dados["CODCFO"]:
        dados["CODCFO"] = cfo_flan.strip()

      dados["BOLETOS"].append({
          "NUMERO_DOCUMENTO": num_doc.strip() if num_doc else None,
          "CODBARRABOLETO": cod_barras.strip() if cod_barras else None,
          "LINHADIGITAVELBOLETO": linha_dig.strip() if linha_dig else None,
          "QRCODEPIX": pix.strip() if pix else None,
      })

    # 4. Buscar dados do cliente na FCFO
    if dados["CODCFO"]:
      query_fcfo = "SELECT NOME, EMAIL, FAX FROM FCFO WHERE CODCFO = ?"
      cursor.execute(query_fcfo, (dados["CODCFO"],))
      cliente = cursor.fetchone()
      if cliente:
        dados["CLIENTE_NOME"] = cliente[0].strip() if cliente[0] else None
        dados["EMAIL"] = cliente[1].strip() if cliente[1] else None
        dados["WHATSAPP"] = cliente[2].strip() if cliente[2] else None

    return dados

  except Exception as e:
    print(f"Erro ao processar consulta no BD para o pedido {numero_input}: {e}")
    return None
  finally:
    con.close()