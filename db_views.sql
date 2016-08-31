DROP VIEW IF EXISTS "invoices";
CREATE VIEW "invoices" AS
SELECT client.name client_name,
       substr(invoice.no, 0, 3) || '-' || substr(invoice.no, 3) `no`,
       substr(project.no, 0, 3) || '-' || substr(project.no, 3) project_no,
       invoice.date,
       cast(strftime('%Y', invoice.date) as integer) year,
       cast(strftime('%m', invoice.date) as integer) month,
       cast(strftime('%d', invoice.date) as integer) day,
       round(coalesce(amount, 0), 2) amount,
       round(coalesce(old_amount, 0) + coalesce(paid, 0), 2) paid,
       round(coalesce(amount, 0) - coalesce(old_amount, 0) - coalesce(paid, 0), 2) balance,
       invoice.name,
       project.name project_name
FROM armgmt_invoice invoice
LEFT JOIN armgmt_client client ON client.id = invoice.client_id
LEFT JOIN armgmt_project project ON project.id = invoice.project_id
LEFT JOIN
  (SELECT invoice_id,
          sum(qty * unit_price) amount
   FROM armgmt_invoicelineitem
   GROUP BY invoice_id) billed ON billed.invoice_id = invoice.id
LEFT JOIN
  (SELECT invoice_id,
          sum(qty * unit_price) old_amount
   FROM armgmt_invoicelineitem l
   INNER JOIN armgmt_invoice i ON i.id = l.invoice_id
   WHERE i.date < '2012-09-01'
   GROUP BY invoice_id) old_billed ON old_billed.invoice_id = invoice.id
LEFT JOIN
  (SELECT invoice_id,
          sum(amount) paid
   FROM armgmt_payment
   GROUP BY invoice_id) paid ON paid.invoice_id = invoice.id
ORDER BY `no` ASC;

DROP VIEW IF EXISTS "payments";
CREATE VIEW "payments" AS
SELECT payment.date,
       cast(strftime('%Y', payment.date) as integer) year,
       cast(strftime('%m', payment.date) as integer) month,
       cast(strftime('%d', payment.date) as integer) day,
       substr(invoice.no, 0, 3) || '-' || substr(invoice.no, 3) invoice_no,
       payment.amount
FROM armgmt_payment payment
LEFT JOIN armgmt_invoice invoice ON invoice.id = payment.invoice_id
UNION
SELECT invoice.date,
       cast(strftime('%Y', invoice.date) as integer) year,
       cast(strftime('%m', invoice.date) as integer) month,
       cast(strftime('%d', invoice.date) as integer) day,
       substr(invoice.no, 0, 3) || '-' || substr(invoice.no, 3) invoice_no,
       round(sum(qty * unit_price), 2) old_amount
FROM armgmt_invoicelineitem l
INNER JOIN armgmt_invoice invoice ON invoice.id = l.invoice_id
WHERE invoice.date < '2012-09-01'
GROUP BY invoice_id
ORDER BY payment.date ASC;
