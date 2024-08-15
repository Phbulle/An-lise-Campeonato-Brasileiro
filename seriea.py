import pandas as pd
import requests
from io import StringIO
from scipy.stats import poisson
from tabulate import tabulate

requisicao = requests.get("https://pt.wikipedia.org/wiki/Campeonato_Brasileiro_de_Futebol_de_2024_-_S%C3%A9rie_A")
conteudo = StringIO(requisicao.text)
tabelas = pd.read_html(conteudo)
tabela_classificacao = tabelas[6]
tabela_jogos = tabelas[7]

print(tabela_jogos)
print(tabela_classificacao)


nomes_times = list(tabela_jogos["Casa \\ Fora"])
siglas = list(tabela_jogos.columns)
siglas.pop(0)

de_para_times = dict(zip(siglas,nomes_times))
tabela_jogos_ajustada = tabela_jogos.set_index("Casa \\ Fora")
tabela_jogos_ajustada = tabela_jogos_ajustada.unstack().reset_index()
tabela_jogos_ajustada = tabela_jogos_ajustada.rename(columns={"level_0":"Fora" , "Casa \\ Fora" : "Casa" , 0:"Resultado"})


def ajustar_sigla_time(linha):
    sigla = linha["Fora"]
    nome = de_para_times[sigla]
    return nome

tabela_jogos_ajustada["Fora"] = tabela_jogos_ajustada.apply(ajustar_sigla_time, axis=1)
tabela_jogos_ajustada = tabela_jogos_ajustada[tabela_jogos_ajustada["Fora"]!=tabela_jogos_ajustada["Casa"]]

tabela_jogos_ajustada["Resultado"] = tabela_jogos_ajustada["Resultado"].fillna(".")

tabela_jogos_realizados = tabela_jogos_ajustada[tabela_jogos_ajustada["Resultado"].str.contains("–")]
tabela_jogos_faltantes = tabela_jogos_ajustada[~tabela_jogos_ajustada["Resultado"].str.contains("–")]
tabela_jogos_faltantes = tabela_jogos_faltantes.drop(columns=["Resultado"])

tabela_jogos_realizados[["Gols_Casa", "Gols_Fora"]] = tabela_jogos_realizados["Resultado"].str.split("–", expand=True)
tabela_jogos_realizados["Gols_Fora"] = tabela_jogos_realizados["Gols_Fora"].astype(int)
tabela_jogos_realizados["Gols_Casa"] = tabela_jogos_realizados["Gols_Casa"].astype(int)

media_gols_casa = tabela_jogos_realizados.groupby("Casa").mean(numeric_only=True)
media_gols_casa = media_gols_casa.rename(columns={"Gols_Casa":"Gols_Feitos_Casa" , "Gols_Fora":"Gols_Sofridos_Casa"})

media_gols_fora = tabela_jogos_realizados.groupby("Fora").mean(numeric_only=True)
media_gols_fora = media_gols_fora.rename(columns={"Gols_Fora":"Gols_Feitos_Fora" , "Gols_Casa":"Gols_Sofridos_Fora"})

tabela_estatisticas = media_gols_casa.merge(media_gols_fora, left_index=True,right_index=True)
tabela_estatisticas = tabela_estatisticas.reset_index()
tabela_estatisticas = tabela_estatisticas.rename(columns={"Casa" : "Times"})


def calcular_pontuacao_esperada(linha):
    #Poisson
    time_casa = linha["Casa"]
    time_fora = linha["Fora"]

    lambda_casa = tabela_estatisticas.loc[tabela_estatisticas["Times"] == time_casa,"Gols_Feitos_Casa"].iloc[0] * tabela_estatisticas.loc[tabela_estatisticas["Times"] == time_fora , "Gols_Sofridos_Fora"].iloc[0]
    lambda_fora = tabela_estatisticas.loc[tabela_estatisticas["Times"] == time_fora,"Gols_Feitos_Fora"].iloc[0] * tabela_estatisticas.loc[tabela_estatisticas["Times"] == time_casa , "Gols_Sofridos_Casa"].iloc[0]

    pv_casa = 0
    p_empate = 0
    pv_fora = 0

    for gols_casa in range(7):
        for gols_fora in range(7):
            probabilidade_resultado = poisson.pmf(gols_casa,lambda_casa) * poisson.pmf(gols_fora,lambda_fora)
            if gols_casa == gols_fora:
                p_empate += probabilidade_resultado
            elif gols_casa > gols_fora:
                pv_casa += probabilidade_resultado
            elif gols_casa < gols_fora:
                pv_fora += probabilidade_resultado

    ve_casa = pv_casa * 3 + p_empate
    ve_fora = pv_fora * 3 + p_empate
    linha["Pontos_Casa"] = ve_casa
    linha["Pontos_Fora"] = ve_fora

    return linha

def atualizar_pontuacao(linha):
    time = linha["Times"]
    pontos_casa = tabela_pontuacao_casa.get(time, 0)
    pontos_fora = tabela_pontuacao_fora.get(time, 0)
    pontuacao = int(linha["Pts"]) + float(pontos_casa) + float(pontos_fora)
    
    return pontuacao

tabela_jogos_faltantes = tabela_jogos_faltantes.apply(calcular_pontuacao_esperada,axis=1)
tabela_classificacao_atualizada = tabela_classificacao[["Equipevde", "Pts"]]
tabela_classificacao_atualizada = tabela_classificacao_atualizada.rename(columns={"Equipevde":"Times"})
tabela_classificacao_atualizada["Pts"] = tabela_classificacao_atualizada["Pts"].astype(int)

tabela_pontuacao_casa = tabela_jogos_faltantes.groupby("Casa").sum(numeric_only=True)["Pontos_Casa"]
tabela_pontuacao_fora = tabela_jogos_faltantes.groupby("Fora").sum(numeric_only=True)["Pontos_Fora"]

tabela_classificacao_atualizada["Pts"] = tabela_classificacao_atualizada.apply(atualizar_pontuacao,axis=1)
tabela_classificacao_atualizada = tabela_classificacao_atualizada.sort_values(by="Pts" , ascending=False,ignore_index=True)
tabela_classificacao_atualizada.index= tabela_classificacao_atualizada.index + 1

print(tabulate(tabela_classificacao_atualizada, headers='keys', tablefmt='fancy_grid'))
print(tabela_estatisticas)
print(tabela_pontuacao_casa)
print(tabela_pontuacao_fora)

