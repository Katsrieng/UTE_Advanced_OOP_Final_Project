from pathlib import Path
import json, re, html, textwrap
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, Preformatted, KeepTogether, Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon, Ellipse
from PIL import Image as PILImage

ROOT=Path(r'D:\UTE_Advanced_OOP_Final_Project')
APP=ROOT/'vehicle_sales_system'
BASE=ROOT/'output'/'report'
OUT=ROOT/'output'/'pdf'; OUT.mkdir(parents=True,exist_ok=True)
W=A4[0]-104
navy=colors.HexColor('#193F5A'); grey=colors.HexColor('#D9D9D9'); pale=colors.HexColor('#F3F6F8')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyR',fontName='Times-Roman',fontSize=11,leading=14,spaceAfter=6,alignment=TA_JUSTIFY))
styles.add(ParagraphStyle(name='SmallR',fontName='Helvetica',fontSize=9,leading=12,spaceAfter=6))
styles.add(ParagraphStyle(name='CaptionR',fontName='Helvetica',fontSize=9,leading=12,spaceBefore=6,spaceAfter=11,textColor=colors.HexColor('#394653')))
styles.add(ParagraphStyle(name='H1R',fontName='Helvetica-Bold',fontSize=19,leading=24,spaceAfter=12,textColor=colors.black))
styles.add(ParagraphStyle(name='H2R',fontName='Helvetica-Bold',fontSize=12,leading=16,spaceBefore=10,spaceAfter=7,textColor=colors.black))
styles.add(ParagraphStyle(name='CellR',fontName='Helvetica',fontSize=8.8,leading=11,spaceAfter=0))
styles.add(ParagraphStyle(name='HeadCellR',fontName='Helvetica-Bold',fontSize=9,leading=12,textColor=colors.white))
pdfmetrics.registerFont(TTFont('ReportMono',r'C:\Windows\Fonts\consola.ttf'))
styles.add(ParagraphStyle(name='CodeR',fontName='ReportMono',fontSize=8.5,leading=10.5,spaceAfter=9))
styles.add(ParagraphStyle(name='CoverR',fontName='Helvetica-Bold',fontSize=27,leading=35,alignment=TA_CENTER,spaceAfter=16))
story=[]; sections=[]
def p(s,style='BodyR'): story.append(Paragraph(s,styles[style]))
def h(s): p(s,'H2R')
def page(title):
    if story: story.append(PageBreak())
    sections.append(title); p(title,'H1R')
def table(headers,rows,widths=None):
    data=[[Paragraph(html.escape(str(v)),styles['HeadCellR']) for v in headers]]
    data += [[Paragraph(html.escape(str(v)).replace('\n','<br/>'),styles['CellR']) for v in row] for row in rows]
    t=Table(data,colWidths=[W*x for x in widths] if widths else None,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,pale]),('GRID',(0,0),(-1,-1),.4,grey),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    t.spaceAfter=7
    story.append(t)
def code(s):
    wrapped='\n'.join('\n'.join(textwrap.wrap(line,98,replace_whitespace=False,drop_whitespace=False)) if len(line)>98 else line for line in s.strip().splitlines())
    story.append(Preformatted(wrapped,styles['CodeR']))
class CropImage(Flowable):
    def __init__(self,path,rect,maxh):
        super().__init__(); self.path=str(path); self.rect=rect
        self.iw,self.ih=PILImage.open(path).size
        self.factor=min(W/rect[2],maxh/rect[3]); self.width=rect[2]*self.factor; self.height=rect[3]*self.factor
        self.hAlign='CENTER'
    def draw(self):
        c=self.canv; x,y,w,h=self.rect; s=self.factor
        c.saveState(); clip=c.beginPath(); clip.rect(0,0,self.width,self.height); c.clipPath(clip,stroke=0)
        c.drawImage(self.path,-x*s,-(self.ih-y-h)*s,width=self.iw*s,height=self.ih*s)
        c.restoreState()
def shot(name,caption,maxh=260):
    path=BASE/'evidence'/f'{name}.png'; im=PILImage.open(path); scale=min(W/im.width,maxh/im.height)
    if name=='invoice-detail': story.append(CropImage(path,(262,212,680,714),maxh))
    else: story.append(Image(str(path),width=im.width*scale,height=im.height*scale,hAlign='CENTER'))
    p(caption,'CaptionR')
def box(d,x,y,w,h,title,lines):
    d.add(Rect(x,y,w,h,fillColor=colors.white,strokeColor=navy,strokeWidth=.8))
    d.add(Rect(x,y+h-25,w,25,fillColor=pale,strokeColor=navy,strokeWidth=.8))
    d.add(String(x+8,y+h-17,title,fontName='Helvetica-Bold',fontSize=10))
    for i,line in enumerate(lines): d.add(String(x+8,y+h-41-i*13,line,fontName='Helvetica',fontSize=8.8))
def edge(d,pts,label='',lx=None,ly=None,arrow=False):
    for a,b in zip(pts,pts[1:]): d.add(Line(*a,*b,strokeColor=navy,strokeWidth=.8))
    if label: d.add(String(lx,ly,label,fontName='Helvetica',fontSize=8.5,fillColor=navy))
    if arrow:
        x,y=pts[-1]; px,py=pts[-2]
        if x==px: poly=[x,y,x-3,y+(6 if py>y else -6),x+3,y+(6 if py>y else -6)]
        else: poly=[x,y,x+(6 if px>x else -6),y-3,x+(6 if px>x else -6),y+3]
        d.add(Polygon(poly,fillColor=navy,strokeColor=navy))
def architecture():
    d=Drawing(W,390)
    labels=[('Browser and presentation',['Jinja templates, CSS, JavaScript','Forms, listings, dashboards, printable invoices']),('Flask routes',['web blueprint and feature route modules','Authentication, CSRF, permission checks, request parsing']),('Service objects',['SalesService, InventoryService, UserService','Business rules and transaction boundaries']),('Repository collection',['MySQLRepository and entity repositories','Parameterized SQL, mapping, joins and reporting']),('Database',['Database connection and transaction owner','MySQL 8 InnoDB, foreign keys and unique constraints'])]
    for i,(title,lines) in enumerate(labels):
        y=310-i*76; box(d,40,y,W-80,64,title,lines)
        if i<4: edge(d,[(W/2,y),(W/2,y-12)],arrow=True)
    return d
def domain_diagram():
    d=Drawing(W,425)
    box(d,0,292,148,111,'User',['id, username, status','full_name, email','password hash in persistence'])
    box(d,172,292,148,111,'Customer',['id, code, name','phone, email, address','status'])
    box(d,344,292,147,111,'Vehicle',['id, code, vin, plate','brand, model, year','price, status, image'])
    box(d,0,92,148,112,'StockMovement',['id, vehicle_id, user_id','date, movement, quantity','reason'])
    box(d,172,92,148,112,'Sale',['id, user_id, customer_id','vehicle_id, price, discount','total, date, status'])
    box(d,344,92,147,112,'Invoice',['id, code, sale_id','date, total'])
    edge(d,[(74,292),(74,204)],'1 : 0..*',80,246)
    edge(d,[(110,292),(110,252),(208,252),(208,204)],'1 : 0..*',129,259)
    edge(d,[(246,292),(246,204)],'1 : 0..*',252,228)
    edge(d,[(405,292),(405,248),(291,248),(291,204)],'1 : 0..1',315,255)
    edge(d,[(435,292),(435,222),(140,222),(140,204)],'Vehicle 1 : movements 0..*',320,227)
    edge(d,[(320,145),(344,145)])
    d.add(String(319,161,'1 : 0..1',fontName='Helvetica',fontSize=8))
    box(d,65,0,160,62,'Role',['id, name, description, status'])
    box(d,267,0,180,62,'Permission',['id, name, module, action'])
    edge(d,[(225,30),(267,30)],'* : *',236,38)
    d.add(String(0,72,'User * : * Role via user_roles; Role * : * Permission via role_permissions',fontName='Helvetica',fontSize=8.7))
    return d
def erd_ops():
    d=Drawing(W,430)
    box(d,0,285,218,128,'vehicles',['PK vehicle_id','UQ vehicle_code, vin, plate_number','brand, model, vehicle_year, status','purchase_price, selling_price','image_path, mileage, fuel'])
    box(d,274,285,217,128,'customers',['PK customer_id','UQ customer_code','full_name, phone, email','address, is_active'])
    box(d,0,65,218,156,'sales',['PK sale_id','UQ sale_code','FK user_id, customer_id','FK + UQ vehicle_id','sale_date, sale_price','discount_amount, total_amount','status'])
    box(d,274,135,217,98,'invoices',['PK invoice_id; UQ invoice_number','FK + UQ sale_id','issue_date, total_amount'])
    box(d,274,0,217,111,'stock_movements',['PK movement_id','FK vehicle_id, user_id','movement_type, movement_date','reason, quantity'])
    edge(d,[(109,285),(109,221)],'1 : 0..1',115,249)
    edge(d,[(382,285),(382,260),(180,260),(180,221)],'1 : 0..*',260,266)
    edge(d,[(218,181),(274,181)],'1 : 0..1',224,190)
    edge(d,[(218,330),(245,330),(245,56),(274,56)],'1 : 0..*',249,76)
    d.add(String(0,30,'users.user_id -> sales.user_id and stock_movements.user_id',fontName='Helvetica',fontSize=8.8))
    d.add(String(0,14,'Each referenced user has zero or many sales and movements.',fontName='Helvetica',fontSize=8.8))
    return d
def erd_access():
    d=Drawing(W,345)
    box(d,0,226,218,106,'users',['PK user_id; UQ username, email','password_hash, full_name','is_active, timestamps'])
    box(d,274,226,217,106,'roles',['PK role_id; UQ role_name','description, is_active','timestamps'])
    box(d,140,104,218,91,'user_roles',['PK + FK user_id, role_id','assigned_at'])
    box(d,0,0,218,78,'permissions',['PK permission_id; UQ name','module, action, description, active'])
    box(d,274,0,217,78,'role_permissions',['PK + FK role_id, permission_id','created_at'])
    edge(d,[(109,226),(109,207),(186,207),(186,195)],'1 : 0..*',41,204)
    edge(d,[(382,226),(382,207),(304,207),(304,195)],'1 : 0..*',393,207)
    edge(d,[(450,226),(470,226),(470,78)],'1 : 0..*',426,91)
    edge(d,[(218,39),(274,39)],'1 : 0..*',221,49)
    return d
def usecases():
    d=Drawing(W,235)
    d.add(Rect(139,8,350,222,fillColor=None,strokeColor=navy))
    d.add(String(255,215,'IGNITE system boundary',fontName='Helvetica-Bold',fontSize=10))
    cases=[('Admin',183,'Manage users and roles'),('Admin / Manager',138,'Manage vehicles and inventory'),('All three roles',93,'Customers, sales and invoices'),('Admin / Manager',48,'View inventory and sales reports')]
    for actor,y,name in cases:
        d.add(String(0,y,actor,fontName='Helvetica-Bold',fontSize=9))
        d.add(Ellipse(315,y+3,150,17,fillColor=pale,strokeColor=navy))
        d.add(String(315,y,name,fontName='Helvetica',fontSize=9,textAnchor='middle'))
        edge(d,[(109,y+3),(165,y+3)])
    return d

page('IGNITE')
story.append(Spacer(1,40))
p('Vehicle Inventory and Sales<br/>Management System for SMEs','CoverR')
p('FINAL PROJECT REPORT','CoverR')
story.append(Spacer(1,30))
for line in ['University of Technology and Entrepreneurship','Department of Computer Science','Advanced OOP with Python | Class CSM1','Term 5 | Year 2']:
    story.append(Paragraph(line,ParagraphStyle(name='coverline',fontName='Helvetica',fontSize=12,leading=20,alignment=TA_CENTER)))
story.append(Spacer(1,35))
table(['Prepared by','Lecturer'],[['Lay Katsrieng\nSour Chansokpanha\nHeang Sovannara','Sek Socheat']],[.58,.42])
story.append(Spacer(1,25))
p('Report prepared 24 September 2026<br/>Implementation reviewed at commit a2f79b8<br/>Branch refactor/clean-structure','CaptionR')

page('Abstract and report guide')
p('IGNITE is a web application for managing individual vehicles, customers, inventory movements, sales and invoices in a small or medium-sized dealership. The project addresses the risk of inconsistent records when stock and sales information are maintained separately. It combines a browser interface with Python service objects, Flask routes, repositories and a MySQL relational database.')
p('The central workflow completes a sale within one database transaction. It verifies the active operator and customer, locks the available vehicle, records the sale, changes its status to SOLD, records a stock-out movement and creates an invoice. Role-based access control separates administrative, management and sales duties. Vehicle photo validation, decimal money calculations and database constraints provide additional safeguards.')
p('A fresh execution of the existing regression suite passed all 51 tests with no failures or skips. The tests cover normal workflows, rejected input, concurrent sale attempts, rollback, permissions, persistence, seed safety and image handling. Screenshots in this report were captured from an isolated database using the project seed data. They demonstrate implemented screens rather than customer deployment results.')
p('The implementation meets the proposal’s core inventory and sales objectives. It remains a university development system: online payments, accounting, multi-branch synchronization and legal tax invoicing are outside the current scope. No field study or measured business productivity improvement is claimed.')
h('Contents')
table(['Section','Coverage','Page'],[
('1 Introduction','Background, problem, objectives and scope','3'),('2 Technology Review','Flask, MySQL, OOP and related systems','4'),('3 Analysis and Design','Requirements, use cases, architecture, classes and ERD','6'),('4 Implementation','Packages, key decisions, code and screenshots','13'),('5 Testing and Results','Execution evidence, test cases, corrections and security','20'),('6 Conclusion','Achievements, limitations, lessons and future work','23'),('Appendices A to D','SQL, user manual, Git evidence and team log','24'),('References','Proposal, lecturer requirements, code and official documentation','31')],[.3,.62,.08])
p('Evidence basis: supplied proposal and lecturer screenshot; current source, schema and tests; read-only Git history; fresh test run and isolated browser captures on 24 September 2026. Individual contribution details require team confirmation.','SmallR')

page('1 Introduction')
h('1.1 Background')
p('A dealership handles distinct physical assets. Two vehicles can share a brand, model and year but still require separate records because their VINs, prices, condition and sales histories differ. Inventory therefore needs to identify each vehicle and connect it to the people and transactions that affect its availability.')
p('The proposal identifies manual records, spreadsheets and separate files as possible sources of delay and inconsistency for vehicle-selling SMEs [1]. IGNITE responds with a centralized application in which authorized staff can search vehicle records, maintain customer information and follow a sale through to its invoice. This motivation comes from the project proposal; it is not presented as the result of an external dealership survey.')
h('1.2 Problem statement')
p('When inventory and sales are updated independently, staff may see an outdated availability status, duplicate a sale or lose the connection between a vehicle, customer and invoice. Uncontrolled editing can also expose administrative functions to users who do not need them. The technical problem is to maintain these relationships and enforce business rules consistently across browser requests and database writes.')
h('1.3 Objectives')
table(['Objective from the proposal','Implemented response'],[
('Manage individual vehicle records','Create, list, filter, edit and view vehicles; preserve historical records through deactivation.'),('Track inventory movements','Record STOCK_IN, STOCK_OUT and ADJUSTMENT against a vehicle and operator.'),('Process sales and invoices','Complete sale, update availability, record stock-out and issue invoice atomically.'),('Control user access','Authenticate active users and authorize actions using role permissions.'),('Apply layered OOP design','Separate dataclasses, services, repositories, routes and database connection ownership.')],[.35,.65])
h('1.4 Scope and stakeholders')
p('The main operators are Admin, Manager and Sales Staff. An SME owner can use an authorized account to review business information, while customers receive invoice information without a customer login portal. The system covers one dealership workspace and uses USD in its interface. Online payment, GPS tracking, a native mobile application, external registration checks, AI pricing, multi-branch synchronization and full accounting remain excluded, consistent with the proposal [1].')

page('2 Technology Review')
h('2.1 Python and Flask')
p('Python supports the project’s domain records, business services, validation and tests. Flask provides routing, request handling and an explicit application object; its factory pattern supports constructing separate application instances for testing [3]. IGNITE implements create_app in app/__init__.py and keeps the local launch entry point in app.py. Jinja renders server-side HTML, while CSS and vanilla JavaScript implement the interface.')
p('This stack keeps the project runnable without a separate frontend build process. It also makes the separation between request handling and business operations visible for an Advanced OOP course. The application uses direct MySQL queries through repositories rather than an object-relational mapper. Consequently, transaction boundaries and SQL mapping are explicit responsibilities of the project code.')
h('2.2 MySQL and persistent relationships')
p('MySQL stores ten tables using InnoDB. Foreign keys connect vehicles, customers, operators, sales and invoices; junction tables implement the many-to-many access relationships. Unique constraints prevent duplicate vehicle codes and duplicate sales of the same vehicle. CHECK constraints restrict status values and monetary relationships.')
p('A normal read is not sufficient when two requests may sell the same vehicle. MySQL locking reads using SELECT ... FOR UPDATE lock selected rows within a transaction [4]. IGNITE combines these locks with a unique sales.vehicle_id constraint and rollback handling. The database layer uses READ COMMITTED isolation for service transactions. These mechanisms are verified by the concurrent-sale and rollback tests, rather than assumed from the interface alone.')
h('2.3 Verified development environment')
table(['Component','Observed version or use'],[
('Python','3.14.6 in the project virtual environment'),('Flask','3.1.3'),('MySQL Connector/Python','9.7.0'),('MySQL server','8.0.46; tests require actual MySQL 8'),('Pillow','12.3.0 for validating and re-encoding photos'),('python-dotenv','1.2.3 for local configuration'),('Rendering and interface','Jinja templates, responsive CSS and vanilla JavaScript'),('Testing and version control','unittest and Git; refactor/clean-structure branch')],[.4,.6])
p('These are the observed versions used for this report, not a promise that every future installation will resolve to the same packages. requirements.txt specifies supported ranges. Credentials and the session secret are supplied through environment configuration and are omitted from this report.','SmallR')

page('2 Technology Review continued')
h('2.4 Object-oriented programming in IGNITE')
p('The implementation uses eight domain dataclasses: User, Role, Permission, Vehicle, Customer, Sale, StockMovement and Invoice. Dataclasses generate record methods from declared fields [5]. Most of these objects represent data rather than implementing all business behavior themselves. Services own the workflows, which is an important distinction from the broader model responsibilities described in the proposal.')
table(['OOP concept','Concrete project example','Reason'],[
('Encapsulation','Database.transaction; VehiclePhotoService','Centralizes connection ownership and file lifecycle rules.'),('Abstraction','MySQLRepository exposes get, save, transaction and queries','Services describe business operations without repeating SQL.'),('Inheritance','VehicleRepository and other entity repositories extend EntityRepository','Reuses projection, lookup, persistence and mapping behavior.'),('Polymorphism','Common repository operations use each subclass’s fields, model and table','A shared interface works with different entity definitions.'),('Composition','SalesService receives a repository; VehicleService receives a photo service','Collaborating objects keep responsibilities separate.'),('Value object','Frozen SaleAmounts with calculate and total','Keeps validated decimal price and discount together.')],[.19,.46,.35])
p('The repository mapper converts dataclass records back to dictionaries so existing templates and route contracts remain compatible. This choice preserves the interface while making domain fields explicit. It is not a fully domain-driven model: many validation rules are intentionally located in services and form helpers.')
h('2.5 Related approaches')
p('A spreadsheet can list vehicle attributes, but relationships, concurrent sales and permissions would need additional conventions or automation. IGNITE implements these rules centrally. A general inventory system offers a broader comparison: Odoo documents unique serial-number tracking and traceability for individual products [6]. IGNITE applies a narrower concept to vehicles by keeping one row per physical vehicle and associating its movement and sale history.')
p('This comparison concerns design scope, not measured performance or product superiority. IGNITE does not implement the breadth of warehouse, procurement or accounting functions found in a larger enterprise system. Its educational value lies in a complete, inspectable vehicle sale workflow and a clear separation of Python responsibilities.')

page('3 Analysis and Design')
h('3.1 Functional and nonfunctional requirements')
table(['ID','Requirement','Verification basis'],[
('FR01','Authenticate active users and reject unauthorized actions.','Login, CSRF and server permission tests.'),('FR02','Maintain searchable, filterable vehicle records and optional photos.','Vehicle forms, pagination and photo tests.'),('FR03','Maintain customer details and retain customer history.','Customer forms and detail routes.'),('FR04','Record legal stock transitions for a physical vehicle.','Inventory transition tests.'),('FR05','Allow a sale only for an available vehicle and active participants.','Sale success, invalid-sale and concurrency tests.'),('FR06','Create one invoice and stock-out entry with each completed sale.','Atomic sale and forced-failure tests.'),('FR07','Present totals, status counts and date-filtered sales information.','Report/decimal tests and browser screenshots.'),('FR08','Manage accounts, role assignment and role permissions.','Role, inactive-user and last-admin tests.'),('NFR01','Preserve data across application instances.','Fresh-app persistence integration test.'),('NFR02','Keep related sale writes consistent under errors and concurrency.','Rollback and duplicate-sale tests.'),('NFR03','Separate presentation, rules and persistence for maintainability.','Package and source inspection.'),('NFR04','Handle invalid input and database outages predictably.','Validation and friendly 503 tests.')],[.13,.5,.37])
h('3.2 Seed role permissions')
table(['Function','Admin','Manager','Sales Staff'],[
('View vehicles, customers, sales, invoices','Yes','Yes','Yes'),('Create/update customers and complete sales','Yes','Yes','Yes'),('Create/update vehicles; manage inventory','Yes','Yes','No'),('View reports','Yes','Yes','No'),('Vehicle deactivation permission','Yes','No','No'),('Manage users and role permissions','Yes','No','No')],[.55,.15,.15,.15])
p('This matrix describes database/seed.sql defaults. Administrators can edit permitted role grants, so a working database may differ. The schema supports multiple roles per user, but the current account editor assigns one role. The proposed Assistant role is future work.','SmallR')

page('3 Use cases')
story.append(usecases())
p('Figure 3.1. Main actor associations under the default seeded permissions. Every use case requires an authenticated account and the relevant server-side permission.','CaptionR')
h('3.3 Complete a vehicle sale')
table(['Element','Description'],[
('Primary actor','Admin, Manager or Sales Staff with the sales permissions.'),('Preconditions','Active operator; active customer; vehicle status AVAILABLE; valid discount.'),('Normal flow','Open New Sale, select the customer and available vehicle, review price and discount, then submit completion. The service locks records and commits sale, SOLD status, stock-out and invoice together.'),('Postconditions','A completed sale exists, its vehicle is SOLD, one stock-out entry is recorded and one invoice is linked by sale_id.'),('Alternate flow','If another request sold the vehicle, or an input is invalid, reject the sale. If invoice insertion fails, roll back all changes.'),('Boundary','The current workflow completes immediately. It does not implement deposits, instalments, cancellation or refunds.')],[.24,.76])
h('3.4 Record an inventory movement')
p('An authorized operator selects a vehicle, chooses a movement and supplies a reason. STOCK_IN requires INACTIVE and changes it to AVAILABLE. Manual STOCK_OUT changes an in-stock vehicle to INACTIVE. ADJUSTMENT records a zero-quantity note without changing status. SOLD vehicles are rejected by this workflow; a sale has its own stock-out operation.')
h('3.5 Maintain user access')
p('An administrator creates or edits an account and assigns an active role. A new password is hashed before persistence. The service rejects changes that would remove the last active administrator and prevents the current operator from changing their own access through the account editor. Administrative grants are protected from normal role-permission editing.')

page('3 Layered architecture')
story.append(architecture())
p('Figure 3.2. Main write workflow. Read routes may request repository data directly or through ReportService; domain records support mapping and money validation across layers.','CaptionR')
h('3.6 Responsibility boundaries')
p('The presentation layer renders the outcome; it does not decide whether a vehicle can be sold. Routes parse requests, check access and call a service. SalesService and InventoryService coordinate business operations. Entity repositories own table-specific SQL, while MySQLRepository provides a shared collection and joined views. Database owns the connection and transaction context used by all participating repositories.')
p('This arrangement prevents a service from accidentally committing only one part of a sale. It also allows tests to construct a new application with an isolated database. Request teardown closes the request connection, and database exceptions are translated into application-level errors instead of exposing raw SQL or credentials to the user.')

page('3 Class design')
story.append(domain_diagram())
p('Figure 3.3. Domain record associations. Multiplicities show relational possibilities; a successful completed-sale workflow creates exactly one invoice. Attributes are selected for readability rather than listing every timestamp or joined display field.','CaptionR')
h('3.7 Key class behavior')
table(['Class','Implemented responsibility'],[
('SaleAmounts','calculate validates price and discount; total returns their difference using Decimal.'),('SalesService','complete coordinates all writes for a completed sale.'),('InventoryService','record validates physical-vehicle transitions and their signed quantities.'),('UserService','save manages accounts; permissions updates editable role grants.'),('VehiclePhotoService','Validates, stores, replaces and safely cleans up uploaded images.'),('EntityRepository','Provides select, get, save, exists and dataclass mapping.')],[.3,.7])

page('3 Operational database design')
story.append(erd_ops())
p('Figure 3.4. Operational ERD derived from database/schema.sql. PK = primary key; FK = foreign key; UQ = unique. Role tables are shown separately in Figure 3.5.','CaptionR')
h('3.8 Integrity and historical records')
p('A vehicle may have zero or one sale because sales.vehicle_id is unique. A sale may have at most one stored invoice because invoices.sale_id is unique. The service adds the stronger workflow guarantee that a successfully completed sale receives an invoice. Customers and operators can be linked to many sales, and each vehicle can have many stock movements.')
p('Stock movements do not contain a sale_id foreign key. A sale-generated movement is associated with its vehicle and operator; its reason includes the sale code. This preserves the implemented schema rather than inventing a direct Sale-to-StockMovement relationship. Foreign keys retain identity when a readable code changes. Historical records are preserved through deactivation rather than ordinary hard deletion.')

page('3 Access control database design')
story.append(erd_access())
p('Figure 3.5. Access-control ERD. Composite keys prevent duplicate user-role and role-permission assignments. Permission name denotes permission_name in the physical schema.','CaptionR')
h('3.9 Data design choices')
p('Numeric primary keys carry relationships; readable codes are unique labels. Money uses DECIMAL(14,2). VIN and plate values have uniqueness constraints, and non-null VINs require 17 characters. Vehicle states are AVAILABLE, RESERVED, SOLD and INACTIVE. Sale states permit PENDING, COMPLETED and CANCELLED, but the implemented workflow completes sales immediately; schema options do not establish a cancellation process.')
h('3.10 Proposal and implementation alignment')
table(['Proposal element','Current implementation'],[
('Ten relational tables','All ten are present; actual data types and constraints are reproduced in Appendix A.'),('InvoiceService','Invoice creation is included in the atomic SalesService workflow.'),('Domain validation methods','Most rules are in services/form helpers; SaleAmounts supplies domain money behavior.'),('UserRole and RolePermission classes','Represented as composite-key junction tables and repository operations.'),('Assistant role consideration','Not seeded or implemented as a dedicated role.'),('Delete or deactivate records','Historical records are retained through deactivation.')],[.37,.63])

page('3 Transaction and state rules')
h('3.11 Atomic completion sequence')
table(['Step','Operation','Purpose'],[
('1','Begin a shared transaction at READ COMMITTED.','All participating repositories use one connection.'),('2','Lock operator, customer and vehicle with FOR UPDATE.','Validate current active/available state under concurrent requests.'),('3','Calculate SaleAmounts from stored price and discount.','Reject invalid money and excessive discount.'),('4','Insert sale with a temporary unique code, then assign its ID-based code.','Avoid count-based identifier races.'),('5','Set vehicle SOLD and insert STOCK_OUT quantity -1.','Record both current state and movement history.'),('6','Insert invoice referencing the sale primary key.','Maintain one invoice for the transaction.'),('7','Commit; on any exception roll back.','Prevent partial sales, orphan invoice links or incorrect stock state.')],[.1,.53,.37])
h('3.12 Inventory transitions')
table(['Current state','Operation','Result'],[
('INACTIVE','STOCK_IN, quantity +1','AVAILABLE'),('AVAILABLE or RESERVED','Manual STOCK_OUT, quantity -1','INACTIVE'),('Any non-SOLD state','ADJUSTMENT, quantity 0','State unchanged; reason recorded'),('AVAILABLE','Complete sale, STOCK_OUT -1','SOLD, completed sale and invoice'),('SOLD','Manual inventory operation','Rejected')],[.31,.39,.3])
p('Vehicle registration establishes the initial state. The system does not derive availability solely by summing stock quantities: an adjustment is an audit note, and initial registration is not equivalent to every later stock-in action. The distinction between vehicle state and movement history is necessary when interpreting reports.')
h('3.13 Identifier conventions')
p('Clean seed data uses VEH-001 through VEH-020, SALE-000001 through SALE-000008 and matching INV-000001 through INV-000008. Fictional 17-character VIN-like values, such as 9ZZ1K8R2000000013, are unique testing identifiers rather than certified or registered VINs. The current live sale generator uses SAL- plus a six-digit ID; this differs from the seed’s SALE- prefix and is recorded here as an existing consistency limitation.')

page('4 Implementation')
h('4.1 Package structure')
code('''vehicle_sales_system/
  app.py                         Local server entry point
  config.py                      Environment and upload settings
  app/
    __init__.py                  Application factory
    database.py                  Connection and transaction owner
    models/                      Eight records and money rules
    repositories/
      base.py                    Shared entity repository behavior
      mysql.py                   Repository collection and joined views
      *_repository.py            Entity queries and reporting
    services/                    Business workflows and photo lifecycle
    routes/
      __init__.py                Register the web blueprint
      *_routes.py                Feature request handlers
      shared_routes.py           Common list/form/detail dispatch
      common.py                  Access checks, CSRF and navigation
      form_helpers.py            Parsing and validation
      resource_config.py         Resource fields and metadata
    templates/                   Jinja page templates
    static/                      Styles, scripts and bundled assets
  database/                      Schema, seed, setup and migrations
  tests/                         Regression and integration tests
  docs/                          Implementation and verification notes''')
p('The refactor separates previously combined code by responsibility while preserving the existing web endpoint names and template data contracts. Each entity repository declares its table, fields and model. The shared base creates projections and maps SQL rows through the declared dataclass. Joined details and reporting queries remain in the repository layer.')
h('4.2 Entry point and configuration')
p('app.py creates the Flask application and launches a local server on 127.0.0.1:5000 with debug disabled. Configuration loads DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD and SECRET_KEY from the environment. A missing session secret is rejected. Startup does not seed or reset the database; explicit database/setup.py commands manage initialization.')
h('4.3 Request handling')
p('Feature route modules handle authentication, dashboard, vehicles, customers, inventory, sales, invoices, reports, users and roles. Common resource routes reduce repeated listing and form code. Validation errors preserve submitted form values. A resource identifier comes from server-controlled metadata; SQL values use query parameters instead of concatenating untrusted input into a statement.')

page('4 Key implementation decisions')
h('4.4 Decimal money as a value object')
code('''@dataclass(frozen=True)
class SaleAmounts:
    price: Decimal
    discount: Decimal

    @classmethod
    def calculate(cls, price, discount):
        result = cls(money(price), money(discount))
        if result.discount > result.price:
            raise ValueError(
                "Discount must be between zero and the selling price.")
        return result

    @property
    def total(self):
        return self.price - self.discount''')
p('Listing 4.1. SaleAmounts from app/models/sale.py, with line wrapping adjusted for the report. The money helper rejects non-finite, negative and excessive amounts and quantizes values to two decimal places. The database independently checks the price-discount relationship.','CaptionR')
h('4.5 Shared transaction ownership')
p('Database.transaction starts a transaction, publishes its connection through a ContextVar, commits on success and rolls back on exceptions. Nested service transactions are rejected. This makes SalesService the owner of a whole sale rather than allowing each repository write to commit independently. The repository get operation adds FOR UPDATE only when the caller requests a lock.')
h('4.6 Photo lifecycle')
p('VehiclePhotoService accepts JPEG, PNG and WebP uploads up to 5 MB and 20 million pixels. It validates decoded content against the extension, rejects animation, applies orientation, resizes within 1920 by 1920 pixels and re-encodes without metadata. UUID-based filenames prevent the original client filename from choosing a storage path.')
p('The database stores a relative image path. On replacement, the previous file is deleted only after the database commit and only if no vehicle still references it. Failed writes preserve the previous photo and clean up the new file where safe. Bundled illustrations and paths outside the upload directory are protected from cleanup. A process crash can still leave an orphan file, so database and filesystem operations are not claimed to be one atomic storage transaction.')
h('4.7 Seed and compatibility decisions')
p('Editable sample definitions are centralized in database/seed.py; database/seed.sql contains role and permission reference data. Identifier migration previews its exact changes and checks collisions before application. It changes labels while preserving primary keys and foreign keys. Old internal preference keys, test prefixes and compatibility names are retained intentionally; visible project branding is IGNITE.')

page('4 Login and dashboard screens')
shot('login','Figure 4.1. Current login page with IGNITE branding and the supplied white sports-car illustration. No password is displayed.',245)
shot('dashboard','Figure 4.2. Dashboard from the isolated seeded database: 20 vehicles, 8 available, 8 sold and USD 256,000 completed-sale revenue.',245)
p('The dashboard provides counts, a revenue chart and a featured vehicle. The car artwork is a generic illustration, not evidence of the listed vehicle’s actual appearance. All screenshots in Figures 4.1 to 4.9 were captured on 24 September 2026 from the current source at the reviewed commit.','SmallR')

page('4 Vehicles and inventory screens')
shot('vehicles','Figure 4.3. Vehicle listing with unique codes and VIN-like values, status filters and pagination. Each row represents one physical vehicle.',250)
shot('inventory','Figure 4.4. Inventory movement listing. Movement type, signed quantity and reason describe the history of individual vehicles.',250)
p('The vehicle record is the source of current availability. Movement records explain later stock transitions. Staff use the listing to locate a record, open its details and perform actions permitted for their role.','SmallR')

page('4 Customer and sales screens')
shot('customers','Figure 4.5. Customer listing populated only with the project’s fictional seeded contacts.',250)
shot('sales','Figure 4.6. Sales listing showing completed transactions and cleaned seed sale references.',250)
p('Customer information is linked to sales by customer_id. The New Sale workflow obtains the price from the selected vehicle and sends completion to the server, where availability and amounts are validated again. This server-side check remains necessary even when the interface only presents available vehicles.','SmallR')

page('4 Invoice and reporting screens')
shot('invoices','Figure 4.7. Invoice listing with unique invoice numbers, linked vehicle/customer information and date filters.',250)
shot('reports','Figure 4.8. Reports page combining current inventory information and sales analytics. Period selection applies to supported sales and movement measures.',250)
p('Reports use database aggregation rather than hard-coded totals. Inventory is a current snapshot; the revenue chart covers the last six calendar months within the selected period. These screens demonstrate seeded behavior, not actual dealership revenue.','SmallR')

page('4 Invoice detail')
shot('invoice-detail','Figure 4.9. Invoice INV-000001 linked to SALE-000001 and vehicle VEH-013. The fictional customer and vehicle data come from the central seed.',440)
p('The example displays a USD 30,900.00 subtotal and USD 500.00 discount, producing a USD 30,400.00 total. This connects the sale amount, invoice total and vehicle identity in one view. The page includes a print action and explicitly identifies the document as a development invoice.')
p('The invoice currently joins customer and vehicle information from their records. It does not yet preserve immutable snapshots of every historical address or legal identity field. Consequently, changing source information may affect how an older invoice is displayed. Snapshotting and configured tax/legal details are listed as future work, rather than claimed as completed features.')

page('5 Testing and Results')
h('5.1 Test method and environment')
p('The existing unittest suite was executed against the reviewed project on 24 September 2026. Database tests created uniquely named temporary databases, seeded them and removed only those owned test databases. A separate temporary seeded database supplied the screenshots. The working project database was not reset or reseeded for this report.')
p('The test helper requires MySQL 8 and port 3307. The local MySQL 8.0.46 service was available on port 3306, so a temporary loopback forward exposed it at 3307 without changing application configuration. RUN_MYSQL_TESTS=1 enabled the database tests. The test account needed permission to create and drop its isolated databases.')
table(['Measure','Observed result'],[
('Tests executed','51'),('Passed','51'),('Failures / errors / skipped','0 / 0 / 0'),('unittest-reported duration','103.855 seconds'),('Reviewed commit','a2f79b8f88be18c6748d17bbbe20bd034aa55bd6'),('Source test modules','test_application, test_database_setup, test_identifier_migration, test_mysql_integration, test_vehicle_photos')],[.34,.66])
code('''RUN_MYSQL_TESTS=1
python -m unittest discover -s tests -v

----------------------------------------------------------------------
Ran 51 tests in 103.855s

OK''')
p('Listing 5.1. Command intent and final runner output. DB_HOST and DB_PORT were set for the local test forward. The evidence log is output/report/evidence/test-results.txt in the workspace. The suite result is functional regression evidence, not a security audit or performance benchmark.','CaptionR')
h('5.2 Test distribution')
table(['Module','Count','Focus'],[
('Application','11','Pages, forms, permissions, transactions and inventory'),('Database setup','5','Entry point, schema order, seed definitions and safe names'),('Identifier migration','4','Clean identifiers, preview/apply, collisions and idempotence'),('MySQL integration','11','Persistence, rollback, money, access and seed behavior'),('Vehicle photos','20','Validation, lifecycle, path safety and failure cleanup')],[.35,.13,.52])

page('5 Representative test cases')
table(['Case','Input or action','Expected result','Result'],[
('TC01','Valid login; invalid or absent CSRF token','Valid login succeeds; invalid protected submission rejected.','Pass'),('TC02','Sales Staff requests restricted administrative action','Server refuses action regardless of navigation visibility.','Pass'),('TC03','Complete sale for available vehicle','One sale, one invoice, one stock-out; vehicle SOLD.','Pass'),('TC04','Concurrent attempts to sell the same vehicle','At most one successful sale; duplicate rejected.','Pass'),('TC05','Force invoice write failure during completion','Sale and stock changes roll back.','Pass'),('TC06','Negative/excessive discount or inactive participant','Reject completion without partial record changes.','Pass'),('TC07','Decimal amounts through sale, invoice and report','Exact expected two-decimal totals.','Pass'),('TC08','STOCK_IN, STOCK_OUT and ADJUSTMENT transitions','Legal states change correctly; invalid transitions rejected.','Pass'),('TC09','SQL-injection-shaped search and duplicate unique values','Input treated as data; constraints remain effective.','Pass'),('TC10','Construct fresh app instance','Previously committed data remains available.','Pass'),('TC11','Deactivate last administrator or change own access','Protected access change rejected.','Pass'),('TC12','Disguised, oversized or unsupported image upload','Reject upload while preserving record and old photo.','Pass'),('TC13','Replace/remove photo; simulate save/commit failure','Safe cleanup ordering; no incorrect deletion of old/shared file.','Pass'),('TC14','Preview/apply legacy identifier migration twice','Only planned fields change; repeat is a no-op.','Pass'),('TC15','Identifier collision or inconsistent seed history','Abort safely rather than overwrite unrelated records.','Pass'),('TC16','Database outage','Friendly 503 response without credentials or raw SQL.','Pass')],[.11,.33,.45,.11])
p('These are grouped report cases mapped to the existing test functions, not an assertion that the suite contains only sixteen tests. The full run contains 51 tests. Browser screenshots provide additional display evidence but do not substitute for the transactional assertions.','SmallR')

page('5 Corrections and validation')
h('5.3 Implemented corrections and regression protection')
table(['Issue addressed','Implemented correction','Evidence'],[
('Risk of double-selling or partial sale persistence','Row locks, unique vehicle sale constraint and one transaction.','Concurrency and invoice-failure rollback tests.'),('Combined modules difficult to navigate','Split domain, repository, service and feature route packages.','Current structure and refactor-verification.md.'),('Legacy sample identifiers visible in business records','Clean seed definitions and guarded identifier migration.','Four identifier tests and current screenshots.'),('Uploaded file deletion before a successful save','Post-commit reference-aware cleanup.','Replacement, shared-file and commit-failure tests.'),('Access changes could remove required administration','Last-admin, self-access and protected-grant checks.','User/role integration tests.'),('Raw database failures unsuitable for the interface','Application exceptions and friendly outage response.','Database outage test.')],[.31,.39,.3])
p('This table identifies corrections present in the code and supported by tests or repository documentation. It does not invent a historical bug-discovery date, author or failing-before test run. Historical verification notes describe earlier revisions; the fresh result in Section 5.1 applies to the reviewed commit.')
h('5.4 Validation and security boundaries')
p('The implemented safeguards include password hashing, active-account checks, server-side permission checks, CSRF validation, parameterized query values, bounded fields, database constraints and safe image decoding. Session cookies are HttpOnly and SameSite=Lax; HTTPS-only cookies are configurable for an HTTPS deployment. Local development is bound to loopback with debug disabled.')
p('These controls do not establish production readiness. Login rate limiting, an appropriately restricted deployment database account, a production WSGI server, HTTPS and tested backup/restore procedures remain deployment tasks. Uploaded photos are static resources and are not individually authorization-protected. No penetration test, external security audit, load test or accessibility audit was performed for this report.')
h('5.5 Demonstration results')
p('The fresh sample dashboard showed 20 vehicles: 8 AVAILABLE, 2 RESERVED, 8 SOLD and 2 INACTIVE. The seed produced 12 customers, 8 completed sales, 8 invoices and 31 movements. The eight seeded sale totals sum to USD 256,000. The invoice example independently shows 30,900 minus 500 equals 30,400. These observations demonstrate coherent seeded relationships; they are not evidence of business adoption.')

page('6 Conclusion')
h('6.1 Achievements')
p('IGNITE implements the proposal’s core objective: a centralized, browser-based vehicle inventory and sales system using Python, Flask, MySQL and an object-oriented structure. Users can maintain individual vehicles and customers, inspect movement history, complete sales, view invoices and consult reports according to their permissions. The sale workflow maintains the relationship between availability, sale, stock-out and invoice in one transaction.')
p('The five research and development questions in the proposal can be answered at the implementation level. Centralized records make vehicle information available through one interface. Stock movements retain vehicle/operator/date/reason history. Row locks and uniqueness prevent duplicate sales in the tested scenario. Role permissions control server actions, and layered objects separate rules from persistence and presentation. The project does not yet quantify improvements in staff time or error rates in a real dealership.')
h('6.2 Limitations')
p('The application completes sales immediately and has no refund, cancellation, instalment or payment gateway workflow. A unique vehicle sale relationship also means buy-back and resale are not modelled. RESERVED is a vehicle state rather than a complete reservation subsystem. Inventory is a current snapshot, not a historical valuation or full accounting ledger.')
p('Invoices need legal configuration, tax handling and immutable identity snapshots before production use. VIN-like sample values are fictional and do not demonstrate registration or checksum verification. New sales use SAL- while cleaned seed sales use SALE-. The proposed Assistant role remains unimplemented. Photo storage requires backup alongside the database and can leave orphan files after a process crash.')
h('6.3 Lessons learned')
p('The project illustrates why transaction ownership belongs around a business operation rather than around separate table writes. It also shows that the user interface cannot replace server-side validation: a vehicle may become unavailable after a form is opened. Separating dataclasses, services and repositories makes these rules easier to locate, while preserving dictionary mappings avoids unnecessary template changes.')
p('Tests for rollback, duplicate requests and file cleanup are particularly useful because failures occur between steps that may appear successful individually. Seed repeatability and guarded migration are also part of reliability: development tooling must not silently replace existing records or edited access grants.')
h('6.4 Future work')
p('The next priorities are invoice snapshots and legal configuration, consistent generated identifiers, deployment hardening and a backup/restore rehearsal. Later iterations can implement a defined cancellation/refund state machine, an Assistant role with agreed permissions and formal user acceptance testing. Multi-branch support, external services and advanced analytics should follow only after their additional consistency and privacy requirements are designed.')

schema=(APP/'database'/'schema.sql').read_text(encoding='utf8')
parts=[('A SQL access tables',schema[:schema.index('CREATE TABLE IF NOT EXISTS customers')]),('A SQL customers and vehicles',schema[schema.index('CREATE TABLE IF NOT EXISTS customers'):schema.index('CREATE TABLE IF NOT EXISTS stock_movements')]),('A SQL sales and inventory',schema[schema.index('CREATE TABLE IF NOT EXISTS stock_movements'):])]
for i,(title,sql) in enumerate(parts):
    page('Appendix '+title)
    p('Source: database/schema.sql at a2f79b8. Statements are reproduced in original order; long lines are wrapped for printing. Use database/setup.py for environment-aware initialization.','SmallR')
    code(sql)

page('Appendix B User manual')
h('B.1 Start a local installation')
p('Use Python and MySQL 8.0.16 or later, then open a terminal in vehicle_sales_system. Create a virtual environment and install requirements.txt. For a fresh clone only, copy .env.example to .env and supply the local database settings and a random SECRET_KEY. Do not overwrite an existing .env or copy its secrets into Git.')
code(r'''python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Fresh clone only; keep an existing .env.
Copy-Item .env.example .env
# Edit .env with this installation's MySQL settings and SECRET_KEY.
.\.venv\Scripts\python.exe database/setup.py
.\.venv\Scripts\python.exe app.py''')
p('Open http://127.0.0.1:5000 in the browser and keep the terminal running. The actual local MySQL port used during this review was 3306; the test harness separately requires 3307. Check the installed server and .env rather than assuming the README’s example port matches every machine. Normal startup does not reset records.')
h('B.2 Daily workflows')
table(['Task','Steps'],[
('Sign in','Enter an existing account’s username and password. The sidebar displays permitted modules.'),('Maintain a vehicle','Open Vehicles, choose Add Vehicle, complete identity and price fields, optionally attach a photo, and save. Open a row to inspect or edit it.'),('Track stock','Open Inventory and add a movement. Select a vehicle, movement and reason. Observe the allowed transitions in Section 3.12.'),('Maintain customers','Open Customers, add or edit contact details, then open the record to inspect related history.'),('Complete a sale','Open Sales and New Sale. Select an active customer and available vehicle, review the discount and complete. Inspect the generated invoice.'),('Print an invoice','Open Invoices, choose its number and use Print Invoice. The current document is not a legal tax invoice.'),('Review performance','Open Dashboard or Reports. Apply the required date period and distinguish current inventory from dated sales measures.'),('Manage access','As Admin, use Users and Roles & Permissions. Keep at least one active administrator.'),('End a session','Use Log out, especially on a shared computer.')],[.26,.74])

page('Appendix B Maintenance guidance')
h('B.3 Recover from common problems')
table(['Symptom','Check or action'],[
('Browser cannot connect','Confirm app.py is running, read its startup error and open the displayed loopback address.'),('Database unavailable message','Confirm MySQL is running and .env host, port, database and account are correct. Do not publish the password in a screenshot.'),('Permission denied','Use an account whose active role has the required permission; do not bypass the server check.'),('Vehicle unavailable during sale','Refresh availability. Another valid transaction may have completed first.'),('Photo rejected','Use a valid, non-animated JPEG, PNG or WebP within the configured size and pixel limits.'),('Duplicate code or VIN','Choose the correct existing record or enter a truly distinct value; do not bypass uniqueness.'),('Test database cases skipped','Set RUN_MYSQL_TESTS=1 only in the documented isolated MySQL test environment.')],[.34,.66])
h('B.4 Safe data handling')
p('Back up both MySQL and app/static/uploads/vehicles, because a database-only backup does not contain the image files. Keep real customer data and credentials out of screenshots used for teaching or submission. This report’s application screenshots use fictional seed contacts in a temporary database.')
p('database/migrate_identifiers.py previews recognized legacy sample labels. Its --apply option applies guarded changes and writes backup evidence. Review the preview and maintain a backup before using a migration on a working database. Code changes retain numeric relationships; a sale code is a label, not the foreign key used by its invoice.')
p('Do not use reset/reseed commands against a database containing genuine user-created records. Repeating normal setup is designed to preserve existing records and grants, while inconsistent sample-sale history causes a conflict instead of silent repair. Development reset commands are outside the routine user workflow.')
h('B.5 Reproduce the report checks')
p('At the reviewed commit, install the project requirements, provide an isolated MySQL 8 test environment on port 3307, set RUN_MYSQL_TESTS=1 and run python -m unittest discover -s tests -v. The suite owns fresh uniquely named databases and drops those only. A skipped suite is not evidence that database behavior passed.')
p('For presentation screenshots, initialize a separate sample database and pass it to create_app. Capture login, dashboard, vehicle, inventory, customer, sales, invoice and report pages. Do not switch the working dealership database merely to obtain cleaner screenshots. The temporary report server in this review used port 5002.')

page('Appendix C Git evidence')
h('C.1 Reviewed version')
table(['Item','Observed value'],[
('Repository','Katsrieng/UTE_Advanced_OOP_Final_Project'),('Branch','refactor/clean-structure'),('HEAD','a2f79b8f88be18c6748d17bbbe20bd034aa55bd6'),('Tracking branch','origin/refactor/clean-structure'),('Local status at report inspection','Clean; no ahead/behind difference shown against the locally stored tracking reference.'),('Review boundary','No new remote fetch, push or merge was performed for report preparation. This is local Git evidence, not a claim about later remote changes.')],[.28,.72])
code('''git status -sb
## refactor/clean-structure...origin/refactor/clean-structure

git log -1 --oneline
a2f79b8 refactor project structure and update vehicle sales system''')
h('C.2 Selected development history')
table(['Date','Commit and Git author','Recorded subject'],[
('24 Sep 2026','a2f79b8\nChansokpanhaSour','Refactor project structure and update vehicle sales system'),('24 Sep 2026','b410e28\nKatsrieng','Update IGNITE development passwords'),('23 Sep 2026','ae2c662\nKatsrieng','Merge latest main and keep README'),('23 Sep 2026','4c45cf4\nKatsrieng','Integrate MySQL persistence and IGNITE branding with updated users'),('23 Sep 2026','9827586\nKatsrieng','Implement vehicle photo CRUD with validated uploads and safe cleanup')],[.2,.31,.49])
p('The selected entries are read from git log. Git author strings identify commit metadata; they do not prove every team member’s individual contribution or working hours. Earlier history contains legacy project wording, which is retained as historical evidence rather than rewritten. The repository URL is https://github.com/Katsrieng/UTE_Advanced_OOP_Final_Project.','SmallR')

page('Appendix D Team log')
h('D.1 Team membership')
p('The proposal lists Lay Katsrieng, Sour Chansokpanha and Heang Sovannara. It does not supply a completed individual activity log, student IDs or verified working hours. The available Git history provides limited commit evidence, but it is not sufficient to reconstruct every member’s work. Individual contributions are therefore left unverified rather than invented.')
table(['Team member','Confirmed work and evidence','Dates or hours'],[
('Lay Katsrieng','To be confirmed by the team.','Not supplied'),('Sour Chansokpanha','To be confirmed by the team.','Not supplied'),('Heang Sovannara','To be confirmed by the team.','Not supplied')],[.28,.47,.25])
h('D.2 Evidence-backed project activity log')
table(['Date','Activity visible in evidence','Source'],[
('23 Sep 2026','Vehicle photo CRUD and safe upload cleanup recorded.','Git commit 9827586 and photo tests.'),('23 Sep 2026','MySQL persistence and IGNITE branding integration recorded.','Git commit 4c45cf4 and integration documentation.'),('24 Sep 2026','Package refactor and system updates recorded.','Git commit a2f79b8 and docs/refactor-verification.md.'),('24 Sep 2026','Fresh 51-test run completed with no failures or skips.','Report test-results.txt.'),('24 Sep 2026','Current screens captured using isolated seeded data.','Figures 4.1 to 4.9.')],[.2,.52,.28])
h('D.3 Submission completion note')
p('Before submission, the team should confirm each member’s actual tasks and dates, add student IDs if required by the lecturer, and replace the unverified entries above with agreed evidence. This is the only intentionally incomplete administrative section; implementation descriptions and test outcomes in the report are based on inspected project evidence.')
p('The proposal’s written timeline presents ten weeks, while its appended presentation shows a four-week plan. Neither is treated as an actual completion log. Appendix C and the activity entries above use observed repository dates, avoiding an invented development schedule.')

page('References')
refs=[
('[1]','Lay Katsrieng, Sour Chansokpanha and Heang Sovannara. Vehicle Inventory and Sales Management System for SMEs. Advanced OOP with Python proposal, UTE, Class CSM1, Term 5, Year 2. User-supplied OOP_Proposal.pdf; reviewed 24 September 2026.'),
('[2]','Lecturer-provided Final Report Structure. User-supplied screenshot dated 23 September 2026. Required chapters and appendices reproduced in the report guide.'),
('[3]','Pallets Projects. Design Decisions in Flask. Flask 3.1 documentation. Accessed 24 September 2026. <link href="https://flask.palletsprojects.com/en/stable/design/" color="#193F5A">https://flask.palletsprojects.com/en/stable/design/</link>'),
('[4]','Oracle. MySQL 8.0 Reference Manual, Locking Reads. Accessed 24 September 2026. <link href="https://dev.mysql.com/doc/refman/8.0/en/innodb-locking-reads.html" color="#193F5A">https://dev.mysql.com/doc/refman/8.0/en/innodb-locking-reads.html</link>'),
('[5]','Python Software Foundation. dataclasses - Data Classes. Python documentation. Accessed 24 September 2026. <link href="https://docs.python.org/3/library/dataclasses.html" color="#193F5A">https://docs.python.org/3/library/dataclasses.html</link>'),
('[6]','Odoo. Use serial numbers to track products. Odoo 17.0 documentation. Accessed 24 September 2026. <link href="https://www.odoo.com/documentation/17.0/applications/inventory_and_mrp/inventory/product_management/product_tracking/serial_numbers.html" color="#193F5A">Odoo documentation - serial number tracking</link>'),
('[7]','IGNITE source repository. Commit a2f79b8f88be18c6748d17bbbe20bd034aa55bd6, branch refactor/clean-structure. Primary implementation evidence: app/models, app/services, app/repositories, app/routes, app/database.py and database/schema.sql. <link href="https://github.com/Katsrieng/UTE_Advanced_OOP_Final_Project" color="#193F5A">GitHub project repository</link>'),
('[8]','IGNITE project documentation. README.md, database/README.md and docs/refactor-verification.md at the reviewed commit. Earlier integration documents are historical records, not substitutes for current source inspection.'),
('[9]','IGNITE regression evidence. Existing tests/test_*.py executed on 24 September 2026. Workspace log: output/report/evidence/test-results.txt. 51 passed, 0 failures, 0 errors, 0 skipped.'),
('[10]','IGNITE browser evidence. Figures 4.1 to 4.9 captured from the reviewed source with an isolated seeded MySQL database on 24 September 2026. Sample values are not real dealership transactions.')]
for n,t in refs: p(f'<b>{n}</b> {t}','SmallR')
h('Evidence interpretation')
p('References [1] and [2] define the requested academic scope. References [3] to [6] support the technology review. References [7] to [10] support the implemented design, screenshots and test results. Report diagrams were drawn from the current classes and schema rather than copied from the proposal’s earlier ERD.','SmallR')

def decorate(c,doc):
    c.saveState()
    if doc.page>1:
        c.setFont('Helvetica',8); c.setFillColor(colors.HexColor('#57616B'))
        c.drawString(52,A4[1]-30,'IGNITE | Vehicle Inventory and Sales Management System')
        c.drawRightString(A4[0]-52,28,str(doc.page))
    c.restoreState()
doc=SimpleDocTemplate(str(OUT/'IGNITE_Final_Report.pdf'),pagesize=A4,rightMargin=52,leftMargin=52,topMargin=55,bottomMargin=48,title='IGNITE Vehicle Inventory and Sales Management System Final Report',author='Lay Katsrieng; Sour Chansokpanha; Heang Sovannara')
doc.build(story,onFirstPage=decorate,onLaterPages=decorate)
from pypdf import PdfReader, PdfWriter
pdf_path=OUT/'IGNITE_Final_Report.pdf'
reader=PdfReader(pdf_path)
assert len(reader.pages)==31
writer=PdfWriter(); writer.clone_document_from_reader(reader)
for index,title in enumerate(sections):
    writer.add_outline_item(title,index)
staged=OUT/'IGNITE_Final_Report.bookmarked.pdf'
with staged.open('wb') as stream: writer.write(stream)
staged.replace(pdf_path)
(BASE/'build'/'section-titles.json').write_text(json.dumps(sections,indent=2),encoding='utf8')
print(OUT/'IGNITE_Final_Report.pdf')
