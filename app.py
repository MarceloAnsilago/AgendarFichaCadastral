import streamlit as st
import pandas as pd
from db_supabase import gravar_no_banco, buscar_agendamentos, atualizar_agendamento, get_supabase_client
from supabase import create_client, Client
import os
from urllib.parse import quote
import datetime
import re
from dotenv import load_dotenv
load_dotenv()

def formata_numero(numero):
    # Remove tudo que não for dígito
    numero = re.sub(r'\D', '', numero)
    # Se não começa com 55, adiciona (Brasil)
    if not numero.startswith('55'):
        numero = '55' + numero
    return numero


if "modal_idx" not in st.session_state:
    st.session_state["modal_idx"] = None
# Página fullscreen, sem menu lateral
st.set_page_config(page_title="Painel de Agendamentos", layout="wide", initial_sidebar_state="collapsed")

# # CSS para remover footer e menu hambúrguer
# hide_streamlit_style = """
#     <style>
#     #MainMenu {visibility: hidden;}
#     footer {visibility: hidden;}
#     header {visibility: hidden;}
#     </style>
# """
# st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# st.markdown(
#     "<h1 style='text-align: center; color: #000; margin-bottom: 18px; margin-top: 10px;'>Agendamento de atualização cadastral</h1>",
#     unsafe_allow_html=True
# )
# # Cria o menu de abas personalizado
# selected = option_menu(
#     menu_title=None,  # Oculta título do menu
#     options=["Agendar", "Agendados", "Concluídos", "Dados"],
#     icons=["calendar-plus", "calendar-check", "check-circle", "bar-chart"],  # Ícones (lucide ou bootstrap)
#     orientation="horizontal",
#     styles={
#         "container": {"padding": "0!important", "background-color": "#f0f2f6"},
#         "icon": {"color": "#4f8bf9", "font-size": "20px"}, 
#         "nav-link": {
#             "font-size": "18px",
#             "font-weight": "bold",
#             "text-align": "center",
#             "margin": "0px",
#             "--hover-color": "#e3e5ee",
#         },
#         "nav-link-selected": {"background-color": "#4f8bf9", "color": "white"},
#     }
# )
# CSS para remover footer e menu hambúrguer + Tabs customizados
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    section[data-testid="stSidebar"] {display: none;}
    /* Tabs style */
    .stTabs [data-baseweb="tab"] {
        font-size:18px;
        font-weight:bold;
        color:#4f8bf9;
        padding: 6px 25px 6px 8px !important;
        background: none !important;      /* Sem fundo */
    }
    .stTabs [aria-selected="true"] {
        background: none !important;      /* Remove o fundo azul */
        color: #4f8bf9 !important;        /* Mantém o azul do texto */
        border-radius:8px 8px 0 0;
        border-bottom: 3px solid #ff2e2e !important;  /* Sublinhado vermelho */
    }
    </style>
""", unsafe_allow_html=True)
st.markdown(
    "<h1 style='text-align: center; color: #000; margin-bottom: 18px; margin-top: 10px;'>Agendamento de atualização cadastral</h1>",
    unsafe_allow_html=True
)

# Tabs com emojis simulando ícones
abas = st.tabs([
    "📅 Agendar",
    "📋 Agendados",
    "✅ Concluídos",
    "📊 Dados"
])


# Função para preencher mensagem
def preencher_mensagem(mensagem, row, contato=""):
    campos = {
        "nome": row.get("nome_titular", ""),
        "propriedade": row.get("nome_propriedade", ""),
        "data_agendamento": row.get("data_agendamento", ""),
        "hora_agendamento": row.get("hora_agendamento", ""),
        "cpf": row.get("cpf", ""),
        "municipio": row.get("municipio", ""),
        "contato": contato  # <- Adiciona contato como campo para tags
    }
    for chave, valor in campos.items():
        mensagem = mensagem.replace("{" + chave + "}", str(valor))
    return mensagem

# if selected == "Agendar":
with abas[0]:
    abasage = st.tabs(["Agendar", "Mensagem WhatsApp"])
    with abasage[0]:
        st.markdown("## 📅 Agendar")

        opcao_carregar = st.radio(
            "Quantidade de registros a exibir:",
            options=["Carregar 30 registros", "Carregar tudo"],
            index=0,
            horizontal=True,
            key="carregar_agendar"
        )

        col_filtros = st.columns(4)
        exibir_tudo = col_filtros[0].checkbox("Exibir tudo", value=True)
        exibir_pendentes = col_filtros[1].checkbox("Exibir pendentes", value=False)
        exibir_agendados = col_filtros[2].checkbox("Exibir agendados", value=False)
        exibir_aguardando = col_filtros[3].checkbox("Exibir aguardando resposta", value=False)

        with st.spinner("Carregando registros..."):
            df = buscar_agendamentos()
            status_a_mostrar = []
            if not exibir_tudo:
                if exibir_pendentes:
                    status_a_mostrar.append("Pendente")
                if exibir_agendados:
                    status_a_mostrar.append("Agendado")
                if exibir_aguardando:
                    status_a_mostrar.append("Aguardando resposta")
                if len(status_a_mostrar) > 0:
                    df = df[df["status"].str.capitalize().isin([s.capitalize() for s in status_a_mostrar])]
                else:
                    df = df.iloc[0:0]
            if opcao_carregar == "Carregar 30 registros":
                df = df.head(30)

        st.info("Confira, selecione ou agende os registros abaixo:")

        if df.empty:
            st.warning("Nenhum registro encontrado no banco.")
        else:
            for col in ["celular", "telefone1", "telefone2"]:
                if col not in df.columns:
                    df[col] = ""

            if "id" not in df.columns:
                st.error("O DataFrame não possui coluna 'id'. Não é possível atualizar o banco.")
                st.stop()

            def contatos_ordenados(row):
                contatos = []
                for col in ["celular", "telefone1", "telefone2"]:
                    valor = str(row.get(col, "")).strip()
                    if valor and valor.lower() != "none":
                        contatos.append(valor)
                while len(contatos) < 3:
                    contatos.append("")
                return pd.Series(contatos[:3], index=["Contato 1", "Contato 2", "Contato 3"])

            contatos_df = df.apply(contatos_ordenados, axis=1)
            df_exibe = pd.concat([contatos_df, df], axis=1)

            colunas_ordenadas = [
                "id",
                "Contato 1", "Contato 2", "Contato 3",
                "status",
                "nome_titular",
                "cpf",
                "nome_propriedade",
                "endereco",
                "dono_terra"
            ]
            colunas_exibidas = [col for col in colunas_ordenadas if col in df_exibe.columns and col != "id"]

            tem_contato = (df_exibe["Contato 1"].astype(str).str.strip() != "")
            df_exibe = pd.concat([df_exibe[tem_contato], df_exibe[~tem_contato]], ignore_index=True)

            # Cabeçalho da tabela
            cols_head = st.columns(len(colunas_exibidas))
            titulos = {
                "Contato 1": "Contato 1", "Contato 2": "Contato 2", "Contato 3": "Contato 3",
                "status": "Status", "nome_titular": "Nome", "cpf": "CPF",
                "nome_propriedade": "Nome da Propriedade", "endereco": "Endereço",
                "dono_terra": "Dono da Terra"
            }
            for i, col in enumerate(colunas_exibidas):
                cols_head[i].markdown(
                    f"<div style='font-weight:bold; text-align:center; font-size:15px; padding-bottom:6px;'>{titulos.get(col, col)}</div>",
                    unsafe_allow_html=True
                )
            for idx, row in df_exibe.iterrows():
                row_id = row.get("id") if "id" in row else None
                row_display = {k: row.get(k, "") for k in colunas_exibidas}
                cols = st.columns(len(colunas_exibidas))
                for i, col in enumerate(colunas_exibidas):
                    valor = row_display.get(col, "")
                    if col in ["Contato 1", "Contato 2", "Contato 3"] and str(valor).strip():
                        numero = formata_numero(valor)
                        mensagem_padrao = st.session_state.get("mensagem_padrao", "")
                        msg_final = preencher_mensagem(mensagem_padrao, row, contato=valor)
                        mensagem_wa = quote(msg_final)
                        url_wa = f"https://wa.me/{numero}?text={mensagem_wa}"
                        html = f"""
                        <a href="{url_wa}" target="_blank" style="
                            display:inline-block;
                            background-color:#25D366;
                            color:white;
                            font-weight:bold;
                            padding:8px 18px;
                            border-radius:6px;
                            text-decoration:none;
                            font-size:15px;">
                            <img src="https://cdn.jsdelivr.net/gh/edent/SuperTinyIcons/images/svg/whatsapp.svg" style="height:18px; vertical-align:middle; margin-right:6px;">
                            WhatsApp
                        </a>
                        <div style='font-size:12px; color:#222; margin-top:2px;'>{valor}</div>
                        """
                        cols[i].markdown(html, unsafe_allow_html=True)
                    elif col == "status":
                        cols[i].write(str(valor))
                        abrir = cols[i].button("🗓️ Agendar", key=f"abrir_modal_{idx}")
                        if abrir:
                            st.session_state["modal_idx"] = idx
                    else:
                        cols[i].write(valor)

                # Modal de agendamento
                if st.session_state.get("modal_idx", None) == idx:
                    st.markdown(
                        """
                        <div style='text-align:center; margin-bottom:12px;'>
                            <span style='font-size:38px;'>📅</span>
                            <div style='font-size:30px; font-weight:bold; margin-top:3px;'>Agendamento</div>
                        </div>
                        """, unsafe_allow_html=True
                    )
                    col1, col2 = st.columns([1, 2]) 
                    with col1:
                        st.markdown(f"**Nome:** {row.get('nome_titular', '')}")
                        st.markdown(f"**CPF:** {row.get('cpf', '')}")
                        st.markdown(f"**Nome da Propriedade:** {row.get('nome_propriedade', '')}")
                        st.markdown(f"**Endereço:** {row.get('endereco', '')}")
                        st.markdown(f"**Dono da Terra:** {row.get('dono_terra', '')}")
                        contatos_txt = ", ".join([
                            str(row.get(col, "")) for col in ["celular", "telefone1", "telefone2"]
                            if pd.notna(row.get(col, "")) and str(row.get(col, "")).strip()
                        ])
                        st.markdown(f"**Contato(s):** {contatos_txt}")
                        contatos_txt = ", ".join([
                            str(row.get(col, "")) for col in ["celular", "telefone1", "telefone2"]
                            if pd.notna(row.get(col, "")) and str(row.get(col, "")).strip()
                        ])
                        st.markdown(f"**Contato(s):** {contatos_txt}")

                        # --------- Mensagem personalizada para copiar ---------
                        mensagem_padrao = st.session_state.get("mensagem_padrao", "")
                        # Pega o primeiro contato válido
                        contato_principal = next(
                            (str(row.get(col, "")).strip() for col in ["celular", "telefone1", "telefone2"] if str(row.get(col, "")).strip()),
                            ""
                        )
                        msg_final = preencher_mensagem(mensagem_padrao, row, contato=contato_principal)
 
                  
                    with col2:
                        st.markdown("**Mensagem personalizada para WhatsApp:**")
                        st.code(msg_final, language=None)
                        st.markdown(
                            "<div style='color:#666;font-size:15px;margin-top:8px;'>"
                            "1️⃣ Clique no botão <b>WhatsApp</b> para abrir a conversa.<br>"
                            "2️⃣ Clique no ícone de copiar (<b>📋</b>) acima da mensagem.<br>"
                            "3️⃣ Cole e envie a mensagem no WhatsApp Web.<br>"
                            "<br><b>Dica:</b> Edite o texto-padrão na aba <i>Mensagem WhatsApp</i>!</div>",
                            unsafe_allow_html=True,
                        )


                    st.markdown(
                        "<span style='font-size:19px;'>📅 <b>Definir data/hora</b></span>",
                        unsafe_allow_html=True
                    )
                    col_data, col_hora = st.columns(2)
                    data = col_data.date_input("Data do agendamento", key=f"data_{idx}")
                    hora = col_hora.time_input("Hora do agendamento", key=f"hora_{idx}")

                    observacao = st.text_area("Observações", key=f"obs_{idx}")

                    status_options = ["Aguardando resposta", "Agendado", "Concluido", "Pendente"]
                    current_status = str(row.get("status", "Pendente")).capitalize()
                    col_central = st.columns([1,2,1])
                    novo_status = col_central[1].selectbox(
                        "Status do agendamento",
                        status_options,
                        index=status_options.index(current_status) if current_status in status_options else 3,
                        key=f"status_select_{idx}"
                    )

                    col_btn = st.columns([1, 1])
                    agendar_btn = col_btn[0].button("✅ Confirmar agendamento", key=f"confirmar_{idx}")
                    cancelar_btn = col_btn[1].button("❌ Cancelar", key=f"cancelar_{idx}")

                    if agendar_btn:
                        if row_id is None:
                            st.error("ID não encontrado! Não foi possível atualizar o banco.")
                        else:
                            atualizar_agendamento(
                                int(row_id),
                                novo_status,
                                str(data),
                                str(hora),
                                observacao
                            )
                            st.success(f"Agendamento confirmado! Status: {novo_status}")
                            st.session_state["modal_idx"] = None
                           

                    if cancelar_btn:
                        st.session_state["modal_idx"] = None

                    st.markdown("<hr style='margin: 18px 0;'>", unsafe_allow_html=True)

                st.markdown("<hr style='margin: 5px 0 10px 0; border:0; border-top:1.5px solid #eaeaea;'>", unsafe_allow_html=True)

    with abasage[1]:
      
        st.markdown("## 💬 Mensagem WhatsApp")
        st.text_area(
            "Digite abaixo a mensagem que deseja enviar pelo WhatsApp:",
            value=(
                "*Olá, tudo bem? 😃 Essa é uma mensagem da IDARON de São Miguel do Guaporé.*\n"
                "O número {contato} está cadastrado na AGÊNCIA IDARON para contato com o produtor {nome}.\n"
                "Você é ele ou responde por ele?\n"
                "*Precisamos falar sobre seu cadastro na Agência.*"
            ),
            height=120,
            key="mensagem_padrao"
        )
        st.markdown(
            """
            <small>Você pode usar as tags:<br>
            <code>{nome}</code>, <code>{propriedade}</code>, <code>{data_agendamento}</code>, <code>{hora_agendamento}</code>, <code>{cpf}</code>, <code>{municipio}</code>,<code>{contato}</code>
            </small>
            """, unsafe_allow_html=True
        )

with abas[1]:
    ab = st.tabs(["Agendados", "Mensagem WhatsApp"])

    with ab[0]:
        st.markdown("## 📋 Agendados")
        st.info("Aqui serão listados apenas os agendamentos confirmados.")

        # SELETOR DE QUANTIDADE
        opcao_carregar = st.radio(
            "Quantidade de registros a exibir:",
            options=["Carregar 30 registros", "Carregar tudo"],
            index=0,
            horizontal=True,
            key="carregar_agendados"
        )

        with st.spinner("Carregando registros..."):
            df = buscar_agendamentos()
            df = df[df["status"].str.lower() == "agendado"]

            if opcao_carregar == "Carregar 30 registros":
                df = df.head(30)

        if df.empty:
            st.warning("Nenhum registro agendado encontrado.")
        else:
            for col in ["celular", "telefone1", "telefone2"]:
                if col not in df.columns:
                    df[col] = ""

            if "id" not in df.columns:
                st.error("O DataFrame não possui coluna 'id'. Não é possível visualizar.")
                st.stop()

            colunas_ordenadas = [
                "id", "status", "data_agendamento", "hora_agendamento",
                "nome_titular", "cpf", "nome_propriedade", "endereco", "dono_terra"
            ]
            colunas_exibidas = [col for col in colunas_ordenadas if col in df.columns and col != "id"]

            # Prioriza linhas com pelo menos um contato
            tem_contato = (
                df["celular"].astype(str).str.strip() != ""
            ) | (df["telefone1"].astype(str).str.strip() != "") | (df["telefone2"].astype(str).str.strip() != "")
            df = pd.concat([df[tem_contato], df[~tem_contato]], ignore_index=True)

            cols_head = st.columns(len(colunas_exibidas))
            titulos = {
                "status": "Status",
                "data_agendamento": "Data Agendamento",
                "hora_agendamento": "Hora Agendamento",
                "nome_titular": "Nome",
                "cpf": "CPF",
                "nome_propriedade": "Nome da Propriedade",
                "endereco": "Endereço",
                "dono_terra": "Dono da Terra"
            }
            for i, col in enumerate(colunas_exibidas):
                cols_head[i].markdown(
                    f"<div style='font-weight:bold; text-align:center; font-size:15px; padding-bottom:6px;'>{titulos.get(col, col)}</div>",
                    unsafe_allow_html=True
                )

            for idx, row in df.iterrows():
                row_id = row.get("id") if "id" in row else None
                row_display = {k: row.get(k, "") for k in colunas_exibidas}
                cols = st.columns(len(colunas_exibidas))
                for i, col in enumerate(colunas_exibidas):
                    valor = row_display.get(col, "")
                    if col == "status":
                        cols[i].write(str(valor))
                        key_btn = f"abrir_modal_{row_id}_{idx}_{col}"  # <-- Chave única
                        abrir = cols[i].button("🔎 Ver agendamento", key=key_btn)
                        if abrir:
                            st.session_state["modal_idx_agendados"] = idx
                    else:
                        cols[i].write(valor)

                # Modal de visualização/edit/reagendamento
                if st.session_state.get("modal_idx_agendados", None) == idx:
                    key_edit = f"editando_{idx}"
                    if key_edit not in st.session_state:
                        st.session_state[key_edit] = False

                    editando = st.session_state[key_edit]
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(
                            """
                            <div style='text-align:center; margin-bottom:12px;'>
                                <span style='font-size:38px;'>📋</span>
                                <div style='font-size:30px; font-weight:bold; margin-top:3px;'>Detalhes do Agendamento</div>
                            </div>
                            """, unsafe_allow_html=True
                        )
                        st.markdown(f"**Nome:** {row.get('nome_titular', '')}")
                        st.markdown(f"**CPF:** {row.get('cpf', '')}")
                        st.markdown(f"**Nome da Propriedade:** {row.get('nome_propriedade', '')}")
                        st.markdown(f"**Endereço:** {row.get('endereco', '')}")
                        st.markdown(f"**Dono da Terra:** {row.get('dono_terra', '')}")

                        data_ag = row.get('data_agendamento', '')
                        hora_ag = row.get('hora_agendamento', '')
                        obs_ag = row.get('observacoes', '') or ""
                        try:
                            data_ag = datetime.date.fromisoformat(data_ag) if data_ag else datetime.date.today()
                        except:
                            data_ag = datetime.date.today()
                        try:
                            hora_ag = datetime.time.fromisoformat(hora_ag) if hora_ag else datetime.datetime.now().time().replace(second=0, microsecond=0)
                        except:
                            hora_ag = datetime.datetime.now().time().replace(second=0, microsecond=0)

                        status_options = ["Aguardando resposta", "Agendado", "Concluido", "Pendente"]
                        current_status = str(row.get("status", "Agendado")).capitalize()
                        col_central = st.columns([1,2,1])

                        if not editando:
                            editar_btn = st.button("🔄 Editar agendamento", key=f"editar_{idx}_agendados")
                            if editar_btn:
                                st.session_state[key_edit] = True

                        if editando:
                            st.markdown(
                                "<span style='font-size:19px;'>📅 <b>Definir data/hora</b></span>",
                                unsafe_allow_html=True
                            )
                            col_data, col_hora = st.columns(2)
                            nova_data = col_data.date_input("Data do agendamento", value=data_ag, key=f"data_{idx}_agendados")
                            nova_hora = col_hora.time_input("Hora do agendamento", value=hora_ag, key=f"hora_{idx}_agendados")
                            nova_obs = st.text_area("Observações", value=obs_ag, key=f"obs_{idx}_agendados")
                            novo_status = col_central[1].selectbox(
                                "Status do agendamento",
                                status_options,
                                index=status_options.index(current_status) if current_status in status_options else 1,
                                key=f"status_select_{idx}_agendados"
                            )
                        else:
                            col_data, col_hora = st.columns(2)
                            col_data.write(f"**Data do agendamento:** {data_ag}")
                            col_hora.write(f"**Hora do agendamento:** {hora_ag}")
                            st.markdown(f"**Observações:** {obs_ag}")
                            col_central[1].write(f"**Status:** {current_status}")
                            nova_data, nova_hora, nova_obs, novo_status = data_ag, hora_ag, obs_ag, current_status

                        col_btns = st.columns([1, 1, 1])
                        if editando:
                            confirmar_btn = col_btns[0].button("✅ Confirmar atualização", key=f"confirmar_{idx}_agendados")
                        else:
                            confirmar_btn = None
                        fechar_btn = col_btns[2].button("❌ Fechar", key=f"fechar_{idx}_agendados")

                        if confirmar_btn:
                            if row_id is None:
                                st.error("ID não encontrado! Não foi possível atualizar o banco.")
                            else:
                                atualizar_agendamento(
                                    int(row_id),
                                    novo_status,
                                    str(nova_data),
                                    str(nova_hora),
                                    nova_obs
                                )
                                st.success(f"Agendamento atualizado! Status: {novo_status}")
                                st.session_state[key_edit] = False
                                st.session_state["modal_idx_agendados"] = None
                        

                        if fechar_btn:
                            st.session_state[key_edit] = False
                            st.session_state["modal_idx_agendados"] = None

                    with col2:
                        st.markdown("<div style='height:60px;'></div>", unsafe_allow_html=True)
                        st.markdown("<b>Contatos</b>", unsafe_allow_html=True)
                       
                        for contato_col in ["celular", "telefone1", "telefone2"]:
                            valor = row.get(contato_col, "")
                            if pd.notna(valor) and str(valor).strip():
                                numero = formata_numero(valor)
                                mensagem_padrao = st.session_state.get("mensagem_padrao_agendar", "")
                                msg_final = preencher_mensagem(mensagem_padrao, row, contato=valor)
                                mensagem_wa = quote(msg_final)
                                url_whatsapp = f"https://wa.me/{numero}?text={mensagem_wa}"

                                st.markdown(
                                    f"""
                                    <a href="{url_whatsapp}" target="_blank" style="
                                        display:inline-block;
                                        background-color:#25D366;
                                        color:white;
                                        font-weight:bold;
                                        padding:8px 18px;
                                        border-radius:6px;
                                        text-decoration:none;
                                        font-size:15px;
                                        margin-bottom:8px;
                                        ">
                                        <img src="https://cdn.jsdelivr.net/gh/edent/SuperTinyIcons/images/svg/whatsapp.svg" style="height:18px; vertical-align:middle; margin-right:6px;">
                                        WhatsApp
                                    </a>
                                    <div style='font-size:12px; color:#222; margin-top:2px; margin-bottom:10px; word-break:break-all;'>{valor}</div>
                                    """,
                                    unsafe_allow_html=True
                                )
                                # Mostra mensagem pronta para copiar (user-friendly)
                                st.markdown("**Mensagem personalizada para WhatsApp:**")
                                st.code(msg_final, language=None)

                        st.markdown(
                            "<div style='color:#666;font-size:15px;margin-top:8px;'>"
                            "1️⃣ Clique no botão <b>WhatsApp</b> para abrir a conversa.<br>"
                            "2️⃣ Copie a mensagem acima.<br>"
                            "3️⃣ Cole e envie no WhatsApp Web.<br>"
                            "<br><b>Dica:</b> Edite o texto-padrão na aba <i>Mensagem WhatsApp</i>!</div>",
                            unsafe_allow_html=True,
                        )

                    st.markdown("<hr style='margin: 18px 0;'>", unsafe_allow_html=True)

                st.markdown("<hr style='margin: 5px 0 10px 0; border:0; border-top:1.5px solid #eaeaea;'>", unsafe_allow_html=True)

    with ab[1]:
        st.markdown("## 💬 Mensagem WhatsApp")
        st.text_area(
            "Digite abaixo a mensagem que deseja enviar pelo WhatsApp:",
            value=(
                "Olá, tudo bem? Essa é uma mensagem da IDARON de São Miguel do Guaporé.\n\n"
                "Temos um horário agendado para *{nome}* na propriedade *{propriedade}* "
                "no município de *{municipio}*, no dia *{data_agendamento}* às *{hora_agendamento}*.\n\n"
                "Podemos confirmar?"
            ),
                height=140,
            key="mensagem_padrao_agendar"
        )
        st.markdown(
            """
            <small>Você pode usar as tags:<br>
            <code>{nome}</code>, <code>{propriedade}</code>, <code>{data_agendamento}</code>, <code>{hora_agendamento}</code>, <code>{cpf}</code>, <code>{municipio}</code>, <code>{contato}</code>
            </small>
            """, unsafe_allow_html=True
        )




# elif selected == "Concluídos":
with abas[2]:
    st.markdown("## ✅ Concluídos")
    st.info("Aqui aparecerão os agendamentos já finalizados.")

    df = buscar_agendamentos()
    df = df[df["status"].str.lower() == "concluido"]

    if df.empty:
        st.warning("Nenhum registro concluído encontrado.")
    else:
        if "id" not in df.columns:
            st.error("O DataFrame não possui coluna 'id'. Não é possível visualizar.")
            st.stop()

        colunas_ordenadas = [
            "id",
            "status",
            "data_agendamento",
            "hora_agendamento",
            "nome_titular",
            "cpf",
            "nome_propriedade",
            "endereco",
            "dono_terra"
        ]
        colunas_exibidas = [col for col in colunas_ordenadas if col in df.columns and col != "id"]

        # Cabeçalho da tabela
        cols_head = st.columns(len(colunas_exibidas))
        titulos = {
            "status": "Status",
            "data_agendamento": "Data Agendamento",
            "hora_agendamento": "Hora Agendamento",
            "nome_titular": "Nome",
            "cpf": "CPF",
            "nome_propriedade": "Nome da Propriedade",
            "endereco": "Endereço",
            "dono_terra": "Dono da Terra"
        }
        for i, col in enumerate(colunas_exibidas):
            cols_head[i].markdown(
                f"<div style='font-weight:bold; text-align:center; font-size:15px; padding-bottom:6px;'>{titulos.get(col, col)}</div>",
                unsafe_allow_html=True
            )

        # Função para callback de editar (resolve duplo clique)
        def start_edit_concluidos(key):
            st.session_state[key] = True

        for idx, row in df.iterrows():
            row_id = row.get("id") if "id" in row else None
            row_display = {k: row.get(k, "") for k in colunas_exibidas}
            cols = st.columns(len(colunas_exibidas))
            for i, col in enumerate(colunas_exibidas):
                valor = row_display.get(col, "")
                if col == "status":
                    cols[i].write(str(valor))
                    abrir = cols[i].button("🔎 Verificar", key=f"abrir_modal_{idx}")
                    if abrir:
                        st.session_state["modal_idx_concluidos"] = idx
                else:
                    cols[i].write(valor)

            # Modal: leitura e possível edição do status, data, hora, observações
            if st.session_state.get("modal_idx_concluidos", None) == idx:
                key_edit = f"editando_{idx}_concluidos"
                if key_edit not in st.session_state:
                    st.session_state[key_edit] = False

                editando = st.session_state[key_edit]

                st.markdown(
                    """
                    <div style='text-align:center; margin-bottom:12px;'>
                        <span style='font-size:38px;'>✅</span>
                        <div style='font-size:30px; font-weight:bold; margin-top:3px;'>Detalhes do Agendamento Concluído</div>
                    </div>
                    """, unsafe_allow_html=True
                )
                st.markdown(f"**Nome:** {row.get('nome_titular', '')}")
                st.markdown(f"**CPF:** {row.get('cpf', '')}")
                st.markdown(f"**Nome da Propriedade:** {row.get('nome_propriedade', '')}")
                st.markdown(f"**Endereço:** {row.get('endereco', '')}")
                st.markdown(f"**Dono da Terra:** {row.get('dono_terra', '')}")

                data_ag = row.get('data_agendamento', '')
                hora_ag = row.get('hora_agendamento', '')
                obs_ag = row.get('observacoes', '') or ""
                try:
                    data_ag = datetime.date.fromisoformat(data_ag) if data_ag else datetime.date.today()
                except:
                    data_ag = datetime.date.today()
                try:
                    hora_ag = datetime.time.fromisoformat(hora_ag) if hora_ag else datetime.datetime.now().time().replace(second=0, microsecond=0)
                except:
                    hora_ag = datetime.datetime.now().time().replace(second=0, microsecond=0)

                status_options = ["Aguardando resposta", "Agendado", "Concluido", "Pendente"]
                current_status = str(row.get("status", "Concluido")).capitalize()

                if not editando:
                    st.button(
                        "✏️ Editar agendamento",
                        key=f"editar_{idx}_concluidos",
                        on_click=start_edit_concluidos,
                        args=(key_edit,)
                    )
                    col_data, col_hora = st.columns(2)
                    col_data.write(f"**Data do agendamento:** {data_ag}")
                    col_hora.write(f"**Hora do agendamento:** {hora_ag}")
                    st.markdown(f"**Observações:** {obs_ag}")
                    st.write(f"**Status:** {current_status}")
                    nova_data, nova_hora, nova_obs, novo_status = data_ag, hora_ag, obs_ag, current_status
                else:
                    col_data, col_hora = st.columns(2)
                    nova_data = col_data.date_input("Data do agendamento", value=data_ag, key=f"data_{idx}_concluidos")
                    nova_hora = col_hora.time_input("Hora do agendamento", value=hora_ag, key=f"hora_{idx}_concluidos")
                    nova_obs = st.text_area("Observações", value=obs_ag, key=f"obs_{idx}_concluidos")
                    novo_status = st.selectbox(
                        "Status do agendamento",
                        status_options,
                        index=status_options.index(current_status) if current_status in status_options else 2,
                        key=f"status_select_{idx}_concluidos"
                    )

                col_btns = st.columns([1,1,1])
                if editando:
                    confirmar_btn = col_btns[0].button("✅ Confirmar atualização", key=f"confirmar_{idx}_concluidos")
                else:
                    confirmar_btn = None
                fechar_btn = col_btns[2].button("❌ Fechar", key=f"fechar_{idx}_concluidos")

                if confirmar_btn:
                    if row_id is None:
                        st.error("ID não encontrado! Não foi possível atualizar o banco.")
                    else:
                        atualizar_agendamento(
                            int(row_id),
                            novo_status,
                            str(nova_data),
                            str(nova_hora),
                            nova_obs
                        )
                        st.success(f"Agendamento atualizado! Status: {novo_status}")
                        st.session_state[key_edit] = False
                        st.session_state["modal_idx_concluidos"] = None

                if fechar_btn:
                    st.session_state[key_edit] = False
                    st.session_state["modal_idx_concluidos"] = None

                st.markdown("<hr style='margin: 18px 0;'>", unsafe_allow_html=True)

            st.markdown("<hr style='margin: 5px 0 10px 0; border:0; border-top:1.5px solid #eaeaea;'>", unsafe_allow_html=True)




# elif selected == "Dados":
with abas[3]:
    st.markdown("## 📊 Dados")
    st.info("Faça upload da planilha Excel (.xlsx) ou HTML (.html) para análise e gravação no banco de dados.")

    uploaded_file = st.file_uploader("Selecione um arquivo Excel (.xlsx) ou HTML (.html)", type=["xlsx", "html"])

    if uploaded_file is not None:
        ext = uploaded_file.name.split('.')[-1].lower()

        # Leitura do arquivo enviado
        if ext == "xlsx":
            df = pd.read_excel(uploaded_file)
        elif ext == "html":
            dfs = pd.read_html(uploaded_file)
            df = dfs[0]
            if "CPF/CNPJ" in df.columns:
                df.rename(columns={"CPF/CNPJ": "CPF"}, inplace=True)
        else:
            st.warning("Formato de arquivo não suportado.")
            df = None

        if df is not None:
            # Limpa CPF
            if "CPF" in df.columns:
                df["CPF"] = (
                    df["CPF"]
                    .astype(str)
                    .str.replace(r"\D", "", regex=True)
                )

            # Garante que as colunas de contato sempre existam!
            for col in ["celular", "telefone1", "telefone2"]:
                if col not in df.columns:
                    df[col] = ""

            # Adiciona coluna status se não existir
            if "status" not in df.columns:
                df["status"] = "Pendente"
            # Adiciona coluna CPF se não existir
            if "CPF" not in df.columns:
                df.insert(1, "CPF", "")

            # Campos para concatenar (se existirem)
            campos_concatenar = [
                "Nome do Titular da Ficha de bovideos",
                "Nome da Propriedade",
                "Dono da Terra (Imóvel Rural)",
                "Endereço da Prop."
            ]
            def juntar_com_barra(col):
                return ' || '.join([str(x) for x in col if pd.notna(x) and str(x).strip() != ""])

            # Demais campos para pegar o primeiro valor (se existirem)
            campos_first = [
                "Categoria",
                "Ulsav Movimento",
                "Município + Cidade/Distrito",
                "DataCadastro",
                "Cód. Ficha",
                "Apelido do Produtor",
                "Telefone 1",
                "Telefone 2",
                "Celular",
                "status"
            ]

            # Monta o dicionário do agg apenas com colunas existentes
            agg_dict = {}
            for campo in campos_first:
                if campo in df.columns:
                    agg_dict[campo] = "first"
            for campo in campos_concatenar:
                if campo in df.columns:
                    agg_dict[campo] = juntar_com_barra

            if "CPF" in df.columns:
                df_agrupado = df.groupby("CPF", dropna=False).agg(agg_dict).reset_index()
            else:
                df_agrupado = df

            # Monta ordem final das colunas (apenas as presentes)
            colunas_final = (
                ["Nome do Titular da Ficha de bovideos", "CPF", "Categoria", "Nome da Propriedade", "Ulsav Movimento",
                "Dono da Terra (Imóvel Rural)", "Município + Cidade/Distrito", "Endereço da Prop.", "DataCadastro",
                "Cód. Ficha", "Apelido do Produtor", "Telefone 1", "Telefone 2", "Celular", "status",
                "celular", "telefone1", "telefone2"]
            )
            colunas_final = [c for c in colunas_final if c in df_agrupado.columns]

            df_final = df_agrupado.reindex(columns=colunas_final, fill_value="")

            st.success(f"{len(df_final)} registros carregados e prontos para gravação (agrupados por CPF).")
            st.dataframe(df_final, use_container_width=True)

            if st.button("Gravar no Supabase"):
                supabase = get_supabase_client()
                sucesso, erro = 0, 0
                for _, row in df_final.iterrows():
                    data = {
                        "nome_titular": row.get("Nome do Titular da Ficha de bovideos", ""),
                        "cpf": row.get("CPF", ""),
                        "categoria": row.get("Categoria", ""),
                        "nome_propriedade": row.get("Nome da Propriedade", ""),
                        "ulsav_movimento": row.get("Ulsav Movimento", ""),
                        "dono_terra": row.get("Dono da Terra (Imóvel Rural)", ""),
                        "municipio": row.get("Município + Cidade/Distrito", ""),
                        "endereco": row.get("Endereço da Prop.", ""),
                        "data_cadastro": row.get("DataCadastro", ""),
                        "cod_ficha": row.get("Cód. Ficha", ""),
                        "apelido": row.get("Apelido do Produtor", ""),
                        "telefone1": row.get("Telefone 1", ""),
                        "telefone2": row.get("Telefone 2", ""),
                        "celular": row.get("Celular", ""),
                        "status": row.get("status", "Pendente"),
                        # Só adicione se a tabela tiver esses campos:
                        "data_agendamento": row.get("data_agendamento", None),
                        "hora_agendamento": row.get("hora_agendamento", None),
                        "observacoes": row.get("observacoes", ""),
                    }
                    try:
                        res = supabase.table("agendamentos").insert(data).execute()
                        if res.data:
                            sucesso += 1
                        else:
                            erro += 1
                    except Exception as e:
                        erro += 1
                        st.error(f"Erro ao gravar registro: {e}")
                st.success(f"{sucesso} registros gravados com sucesso. {erro} falharam.")