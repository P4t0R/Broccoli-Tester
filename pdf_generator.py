from fpdf import FPDF
import os

def generate_pdf(results, output_file="reporte_apis.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Reporte de APIs", ln=True, align="C")
    pdf.ln(5)

    # ---------------- Resumen Estadístico ----------------
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Resumen Estadístico", ln=True)

    if results:
        tiempos = [r.time for r in results]
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 6, f"Total APIs ejecutadas: {len(results)}", ln=True)
        pdf.cell(0, 6, f"Tiempo mínimo: {min(tiempos):.4f}s", ln=True)
        pdf.cell(0, 6, f"Tiempo máximo: {max(tiempos):.4f}s", ln=True)
        pdf.cell(0, 6, f"Tiempo promedio: {sum(tiempos)/len(tiempos):.4f}s", ln=True)
        pdf.ln(3)

    # ---------------- Sección Detallada ----------------
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Detalle de APIs", ln=True)

    # Tabla de resultados
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(70, 7, "API", border=1, fill=True)
    pdf.cell(30, 7, "Status", border=1, fill=True)
    pdf.cell(30, 7, "Tiempo(s)", border=1, fill=True)
    pdf.ln()

    pdf.set_font("Arial", "", 10)
    fill = False
    for r in results:
        pdf.set_fill_color(240, 240, 240) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(70, 6, r.api_name, border=1, fill=True)
        pdf.cell(30, 6, str(r.status), border=1, fill=True)
        pdf.cell(30, 6, f"{r.time:.4f}", border=1, fill=True)
        pdf.ln()
        fill = not fill

    pdf.output(output_file)
