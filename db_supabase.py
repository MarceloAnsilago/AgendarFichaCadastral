from supabase import create_client, Client
import pandas as pd
import os


def get_supabase_client() -> Client:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL e SUPABASE_KEY precisam estar definidos nas variáveis de ambiente.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def buscar_agendamentos():
    supabase = get_supabase_client()
    response = supabase.table("agendamentos").select("*").execute()
    data = response.data if response and hasattr(response, "data") else []
    df = pd.DataFrame(data)
    return df

def gravar_no_banco(df):
    supabase = get_supabase_client()
    colunas_esperadas = [
        "Nome do Titular da Ficha de bovideos",
        "CPF",
        "Categoria",
        "Nome da Propriedade",
        "Ulsav Movimento",
        "Dono da Terra (Imóvel Rural)",
        "Município + Cidade/Distrito",
        "Endereço da Prop.",
        "DataCadastro",
        "Cód. Ficha",
        "Apelido do Produtor",
        "Telefone 1",
        "Telefone 2",
        "Celular",
        "status",
        "data_agendamento",
        "hora_agendamento",
        "observacoes"
    ]
    for col in colunas_esperadas:
        if col not in df.columns:
            df[col] = ""
    registros = []
    for _, row in df.iterrows():
        registro = {
            "nome_titular": row["Nome do Titular da Ficha de bovideos"],
            "cpf": row["CPF"],
            "categoria": row["Categoria"],
            "nome_propriedade": row["Nome da Propriedade"],
            "ulsav_movimento": row["Ulsav Movimento"],
            "dono_terra": row["Dono da Terra (Imóvel Rural)"],
            "municipio": row["Município + Cidade/Distrito"],
            "endereco": row["Endereço da Prop."],
            "data_cadastro": row["DataCadastro"],
            "cod_ficha": row["Cód. Ficha"],
            "apelido": row["Apelido do Produtor"],
            "telefone1": row["Telefone 1"],
            "telefone2": row["Telefone 2"],
            "celular": row["Celular"],
            "status": row.get("status", "Pendente") or "Pendente",
            "data_agendamento": row.get("data_agendamento"),
            "hora_agendamento": row.get("hora_agendamento"),
            "observacoes": row.get("observacoes", ""),
        }
        registros.append(registro)
    if registros:
        res = supabase.table("agendamentos").insert(registros).execute()
        return res
    return None

def atualizar_agendamento(id, status, data_agendamento, hora_agendamento, observacoes):
    supabase = get_supabase_client()
    res = supabase.table("agendamentos").update({
        "status": status,
        "data_agendamento": data_agendamento,
        "hora_agendamento": hora_agendamento,
        "observacoes": observacoes
    }).eq("id", id).execute()
    return res

# Exemplo de uso rápido
if __name__ == "__main__":
    # Buscar todos
    print(buscar_agendamentos())

    # Exemplo de update:
    # atualizar_agendamento(1, "Concluido", "2024-06-30", "14:00", "Teste update")