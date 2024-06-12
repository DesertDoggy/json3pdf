from reportlab.pdfgen import canvas

def create_pdf(output_filename):
    c = canvas.Canvas(output_filename)
    c.drawString(100, 750, "Hello, World!")
    c.save()

create_pdf("hello_world.pdf")