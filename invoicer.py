#!/usr/bin/env python3

import yaml
import textwrap
import argparse
import os, sys, datetime
from typing import List
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
from reportlab.lib import colors

# settings struct, it contains:
# - output directory
# - invoice header (array of strings)
# - invoice footer (array of strings)
class Settings(BaseModel):
    output_directory: str
    # list of strings
    invoice_header: List[str]
    invoice_footer: List[str]
    # payment instructions
    payment_instructions: dict

SETTINGS_FILE = "~/.config/invoicer.yml"

# global settings variable
settings = None

# struct for invoice item, it contains:
# - description
# - quantity
# - unit price
# - total price
class InvoiceItem(BaseModel):
    description: str
    quantity: float
    unit_price: float

# struct for invoice, it contains:
# - customer name
# - customer address1
# - customer address2
# - customer business number
# - invoice number
# - invoice currency
# - invoice date (italian format)
# - invoice items (array of items, each item contains: description, quantity, unit price, total price)
# - invoice total price
class Invoice(BaseModel):
    customer_name: str
    customer_address1: str
    customer_address2: str
    customer_business_number: str
    invoice_number: int = 0
    invoice_currency: str
    # invoice date is optional, if not specified, it is the current date in italian format
    invoice_date: str = datetime.datetime.now().strftime("%d/%m/%Y")
    invoice_items: List[InvoiceItem]
    # optional field
    invoice_total_price: float = 0.0

    def __init__(self, **data):
        super().__init__(**data)
        # if the invoice date is not specified, it is the current date in italian format
        if not self.invoice_date:
            self.invoice_date = datetime.datetime.now().strftime("%d/%m/%Y")

        # if the invoice number is specified and the file starting with the invoice number already exists, exit
        if self.invoice_number:
            for file in os.listdir(settings.output_directory):
                if file.startswith(str(self.invoice_number)):
                    print(f"Error: file with invoice number {self.invoice_number} already exists")
                    sys.exit(1)

        # if the invoice number is not specified, it is the last invoice number in the output directory (if any) + 1
        if not self.invoice_number:
            self.invoice_number = self.get_next_invoice_number()


    # function that returns the next invoice number
    def get_next_invoice_number(self) -> int:

        # get the invoice number. it is an incremental number based on the last invoice number in the output directory (if any)
        # the invoice files are in this format: {invoice_number}_customer_name.pdf. example: 1_acme.pdf
        # customer_name is the customer name in camel case format
        invoice_number = 1
        for file in os.listdir(settings.output_directory):
            if file.endswith(".pdf") and file.split("_")[0].isdigit():
                # get the invoice number from the file name
                file_invoice_number = int(file.split("_")[0])
                print(f"file_invoice_number: {file_invoice_number}")
                if file_invoice_number >= invoice_number:
                    invoice_number = file_invoice_number + 1
        return invoice_number

# function that reads the settings file and returns a settings dictionary
def read_settings() -> Settings:
    with open(os.path.expanduser(SETTINGS_FILE), 'r') as file:
        settings = yaml.safe_load(file)

    # convert the settings dictionary to a Settings object
    settings = Settings(**settings)

    # if the output directory does not exist, exit
    if not os.path.exists(settings.output_directory):
        print(f"Error: output directory {settings.output_directory} does not exist")
        sys.exit(1)

    return settings

# function that reads the template and returns the invoice
def read_template(template_file: str) -> Invoice:
    # if the template file does not exist, exit
    if not os.path.exists(template_file):
        print(f"Error: template file {template_file} does not exist")
        sys.exit(1)

    with open(template_file, 'r') as file:
        invoice = yaml.safe_load(file)

    # convert the invoice dictionary to an Invoice object
    invoice = Invoice(**invoice)

    return invoice

# function that returns the total price of the invoice
def calculate_total_price(invoice: Invoice) -> float:
    total_price = 0.0
    for item in invoice.invoice_items:
        total_price += item.unit_price * item.quantity
    return total_price

# function that prints the invoice to a pdf file in the output directory.
def print_invoice(invoice: Invoice) -> None:
    print("Invoice")
    print("-------")
    print("Customer Name: " + invoice.customer_name)
    print("Customer Address1: " + invoice.customer_address1)
    print("Customer Address2: " + invoice.customer_address2)
    print("Customer Business Number: " + invoice.customer_business_number)
    print("Invoice Number: " + str(invoice.invoice_number))
    print("Invoice Currency: " + invoice.invoice_currency)
    print("Invoice Date: " + invoice.invoice_date)
    print("Invoice Items:")
    for item in invoice.invoice_items:
        print("\tDescription: " + item.description)
        print("\tQuantity: " + str(item.quantity))
        print("\tUnit Price: " + str(item.unit_price))
        print("\tTotal Price: " + str(item.unit_price * item.quantity))
    print("Invoice Total Price: " + str(calculate_total_price(invoice)))
    print("-------")

# function that outputs the invoice to a pdf file in the output directory.
# the pdf file name is: {invoice_number}_customer_name.pdf. example: 0001_acme.pdf
# customer_name is the customer name in camel case format
def output_pdf(invoice: Invoice, settings: Settings) -> None:
    # check in the settings file if the output directory exists
    if not os.path.exists(settings.output_directory):
        print(f"Error: output directory {settings.output_directory} does not exist")
        sys.exit(1)

    # get the invoice number. it is an incremental number based on the last invoice number in the output directory (if any)
    # the invoice files are in this format: {invoice_number}_customer_name.pdf. example: 1_acme.pdf
    # customer_name is the customer name in camel case format
    invoice_number = invoice.invoice_number

    # in camel case
    customer_name = invoice.customer_name.replace(" ", "_").lower()

    # Prepare the PDF file name and path
    pdf_file_name = f"{settings.output_directory}/{invoice_number}_{customer_name}.pdf"

    # Set up the document
    doc = SimpleDocTemplate(pdf_file_name, pagesize=letter)
    elements = []

    # header table
    header_data = [[header_text] for header_text in settings.invoice_header]
    header_table = Table(header_data)
    header_table.setStyle(TableStyle([
        # first row is bold
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))

    # custgomer table
    customer_data = [
            [invoice.customer_name],
            [invoice.customer_address1],
            [invoice.customer_address2],
            [invoice.customer_business_number],
            [],
            [],
            [],
    ]
    customer_table = Table(customer_data)
    customer_table.setStyle(TableStyle([
        # first row is bold
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))

    combined_table = Table([[header_table, customer_table]], colWidths=[265, 300])

    # Add the table to the elements
    elements.append(combined_table)

    elements.append(Spacer(1, 24))

    # Write the invoice details to the PDF
    invoice_data = [
        ['Invoice Date:', invoice.invoice_date],
        ['Invoice Number:', invoice_number],

    ]
    details_table = Table(invoice_data, colWidths=[240, 300])
    details_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
    ]))
    elements.append(details_table)

    # add whitespace
    elements.append(Spacer(1, 24))

    # Write the invoice items to the PDF
    items_data = [['Description', 'Quantity', 'Unit Price', 'Total Price']]
    for item in invoice.invoice_items:
        # multiline description, do not use Paragraph(item.description, styles["Normal"])
        description = textwrap.fill(item.description, 40)
        quantity = item.quantity
        unit_price = item.unit_price
        total_price = item.unit_price * item.quantity
        items_data.append([description, quantity, unit_price, total_price])

    # add the total price to the invoice and the currency
    items_data.append([f"Tot ({invoice.invoice_currency}):", '', '', f"{calculate_total_price(invoice)} {invoice.invoice_currency}"])

    items_table = Table(items_data, colWidths=[250, 90, 100, 100], repeatRows=1)
    items_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        # last row font is bold
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),

        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    elements.append(items_table)

    # spacer
    elements.append(Spacer(1, 12))

    # payment details
    # payment_instructions:
    #   eur: IT00 0000 0000 0000 0000 00
    #   chf: CH00 0000 0000 0000 0000 0

    payment_data = []

    # get the payment instructions for the invoice currency
    payment_instructions = settings.payment_instructions[invoice.invoice_currency.lower()]
    payment_data.append([payment_instructions])

    payment_table = Table(payment_data, colWidths=[550])
    payment_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(payment_table)

    # spacer
    elements.append(Spacer(1, 12))

    # Add footer to each page
    footer_data = [[footer_text] for footer_text in settings.invoice_footer]
    footer_table = Table(footer_data, colWidths=[550], rowHeights=20)
    footer_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(footer_table)

    # Build the PDF document
    doc.build(elements)

def main( args: argparse.Namespace) -> None:
    global settings
    # if there is no template file, exit
    if not os.path.exists(args.template_file):
        print(f"Error: template file {args.template_file} does not exist")
        sys.exit(1)

    # Read the settings from the file
    settings = read_settings()

    # if settings is none, exit
    if not settings:
        print("Error: settings is None")
        sys.exit(1)

    # Read the template from the file
    invoice = read_template(args.template_file)

    # Print the invoice
    print_invoice(invoice)
    output_pdf(invoice, settings)

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("template_file", help="the template file to use")
    return parser.parse_args()

if __name__ == "__main__":
    main(parse_arguments())
