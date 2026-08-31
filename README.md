## Filament & Order Management System (FOMS)

### Setup
`git clone https://github.com/tabre/foms.git`\
`cd foms`

Create a new .env file in the project root and define the following variables within:
```
PG_IP=
PG_PORT=
PG_DB=
PG_UN=
PG_PW=

FOMS_IP=
FOMS_PORT=

SUBNET=
```

Then:\
`docker compose up --build -d`

In your browser, go to:\
`http://localhost:{FOMS_PORT}`\
Where `{FOMS_PORT}` is whatever you set in your .env file


### Introduction
This project seeks to streamline inventory management and order fulfillment for a small-scale manufacturing operation that relies on filament-based production (3D printing). As demand for custom and premade printed products grows, manual tracking of raw materials (filament by material, color, and other modifiers) and finished goods quickly becomes error-prone and time-consuming. Without a centralized system, the business risks running out of critical materials mid-order, mispricing jobs due to inaccurate material costing, and losing track of order status and fulfillment timelines. Our proposed system addresses these challenges by providing a unified platform that tracks raw material and product inventory in real time, automates inventory deductions per order, and gives management clear visibility into stock levels and order pipelines, all through a simple, easy-to-use interface that doesn’t require deep technical expertise.


### Diagnosis
Filament-based production businesses often manage inventory and orders through disconnected methods such as spreadsheets, sticky notes, or memory. This does not scale well as order volume grows. Filament comes in many types, colors, and special modifiers like matte, silk, and glow-in-the-dark, making manual tracking especially error-prone. When inventory isn’t tracked accurately, staff may not realize a material has run low until mid-print, causing delays and missed deadlines. Similarly, without a structured order intake process, staff may forget critical order details such as material, color, or quantity, or they may lose track of which orders have been fulfilled and when. This project aims to eliminate these gaps by automating inventory deduction, providing proactive low-stock alerts, and giving staff a clear, centralized view of all orders and their fulfillment status.


### Proposed Solution
Our solution directly addresses the problem of manual, error-prone inventory and order tracking by providing an integrated system that connects order intake, inventory deduction, and fulfillment tracking into a single workflow. Rather than requiring staff to cross-reference spreadsheets or physical stock counts, the system automatically calculates material usage per order and updates inventory levels in real time, while giving management the tools to proactively manage stock and monitor order status.
