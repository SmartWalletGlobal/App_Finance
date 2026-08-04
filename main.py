import flet as ft
import pandas as pd

def main(page: ft.Page):
    page.title = "Controle Financeiro Anual"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = "#0F2E22" # Fundo verde escuro executivo

    # Elementos visuais iniciais
    titulo = ft.Text("Meu Financeiro", size=24, weight=ft.FontWeight.BOLD, color="white")
    subtitulo = ft.Text("Visão Geral e Gráficos", size=14, color="#A3E4D7")

    # Botão corrigido compatível com todas as versões recentes do Flet
    btn_lancar = ft.ElevatedButton(
        content=ft.Text("Novo Lançamento", color="white"),
        bgcolor="#1E8449"
    )

    page.add(
        ft.Column(
            [
                titulo,
                subtitulo,
                ft.Container(height=20),
                btn_lancar
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

    page.update()

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550)
