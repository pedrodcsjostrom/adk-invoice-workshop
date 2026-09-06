/*
 * The architecture model of the deployed invoice-analyzer service.
 *
 * Scope: the deployed system only. The local half of the hour — `adk web`,
 * the developer UI, the sandbox as a model backend — is deliberately absent
 * (ADR-0005).
 *
 * Vocabulary comes from CONTEXT.md at the repo root. Where a name appears in
 * the glossary it is spelled here exactly as the glossary spells it, and
 * `tests/test_model_drift.py` fails when that stops being true.
 *
 * Render:  scripts/export_diagrams.sh      (offline, writes docs/architecture/svg)
 * Explore: scripts/export_diagrams.sh serve  (http://localhost:8090)
 */
workspace "ADK invoice workshop" "The deployed invoice-analyzer service an attendee applies to their own Google Cloud project." {

    # The glossary travels with the model, so a term met on a diagram resolves
    # in the same viewer. The decision log is deliberately not attached: the
    # !adrs importer wants a "## Status" section and a date, and without them it
    # imports every ADR silently as Proposed and dated at export time, which is
    # false. Adding front matter to the ADRs to please a diagram tool is the
    # tail wagging the dog, so each element names its ADR in its description
    # instead. Do not attempt this again without changing the ADRs first.
    !docs ../../CONTEXT.md

    model {
        # A component relationship implies the container and system ones above
        # it. Declaring those by hand would be a second place to edit, and one
        # of the two would eventually be wrong.
        !impliedRelationships true

        attendee = person "Attendee" "Anyone in the room. Has done the pre-flight and owns a Google Cloud project."

        originShim = softwareSystem "Origin shim" "Deletes the Origin header on the way to the deployed service. Runs on the attendee's laptop (ADR-0004)." "External"

        gemini = softwareSystem "Vertex AI Gemini" "The model backend. Reads the document, decides which tool to call." "External"

        deployedService = softwareSystem "Deployed service" "The invoice analyzer in the attendee's own Google Cloud project: the upload page, the records page and the agent." {

            cloudRun = container "Cloud Run service" "Serves the upload page and the records page, and runs the agent in-process. Not separately deployable from it." "FastAPI on Cloud Run" "Google Cloud Platform - Cloud Run" {

                uploadPage = component "Upload page and /analyze" "The file picker, which replaces the ADK developer UI on Cloud Run (ADR-0001), and the endpoint each document is posted to on its own rather than to ADK's REST API (ADR-0002). Returns the record and the trace summary; saves nothing itself." "invoice_agent/upload.py"

                recordsPage = component "Records page" "Every invoice filed, newest first, flagged by whether it adds up." "invoice_agent/records.py"

                invoiceAnalyzer = component "invoice_analyzer" "One ADK LlmAgent: the instruction, three tools and one output schema. Steps 3 and 4 of the instruction are the re-read. One run per document, never one run per batch (ADR-0003)." "invoice_agent/agent.py"

                documentGuard = component "Document guard" "The before_model_callback that refuses any turn arriving without document bytes, before the model is called." "invoice_agent/guards.py"

                arithmeticTool = component "check_invoice_arithmetic" "Reports whether the numbers agree. Decides nothing and stores nothing." "invoice_agent/tools.py"

                lookupTool = component "lookup_supplier" "Resolves the supplier name as printed to a supplier_id." "invoice_agent/tools.py"

                saveTool = component "save_invoice_record" "Files the finished record, including one that does not add up." "invoice_agent/tools.py"

                validation = component "Validation" "The arithmetic chain: quantity times unit price per line, lines summing to the printed total, to one cent." "invoice_agent/validation.py"

                supplierRegistry = component "Supplier registry" "The known suppliers and their aliases, read from a JSON file shipped in the repo. Nothing writes to it." "invoice_agent/registry.py, data/vendor_registry.json"

                store = component "Store" "Files the record and archives the document, and decides validation_passed rather than the agent." "invoice_agent/store.py"
            }

            firestore = container "Firestore database" "The invoice records, one document per analysed invoice, in a named database rather than (default)." "Cloud Firestore" "Google Cloud Platform - Cloud Firestore,Database"

            archive = container "Archive bucket" "The original document that was analysed, kept beside its record and deleted after seven days." "Cloud Storage" "Google Cloud Platform - Cloud Storage,Database"
        }

        attendee -> originShim "Runs, then opens the URL it prints"
        originShim -> uploadPage "Proxies uploads to, Origin header deleted" "HTTPS"
        originShim -> recordsPage "Serves the filed records back through" "HTTPS"

        uploadPage -> invoiceAnalyzer "Drives one run per document with an ADK Runner"
        invoiceAnalyzer -> documentGuard "Passes every turn through, before the model"
        documentGuard -> gemini "Sends the turn on, only with document bytes attached" "Vertex AI API"
        invoiceAnalyzer -> arithmeticTool "Calls with the LineItem list and the printed total. Twice, on the rigged invoice"
        invoiceAnalyzer -> lookupTool "Calls once with the supplier name as printed"
        invoiceAnalyzer -> saveTool "Calls once with the finished InvoiceRecord"
        arithmeticTool -> validation "Checks the line items and the total with"
        saveTool -> validation "Checks them again with, which is why the store's answer is trustworthy"
        lookupTool -> supplierRegistry "Matches the printed name through"
        saveTool -> store "Files the InvoiceRecord and the document bytes through"
        recordsPage -> store "Reads the filed records from"
        store -> firestore "Writes the record to" "InvoiceRecord as a document"
        store -> archive "Copies the analysed document into" "Object write"

        deploymentEnvironment "Attendee project" {

            project = deploymentNode "The attendee's Google Cloud project" "One project per attendee, created in the pre-flight and torn down after the hour." "Google Cloud" {

                serviceAccount = infrastructureNode "invoice-agent service account" "Created by the stack rather than the Compute Engine default, whose existence and permissions vary by organization policy. Also holds roles/artifactregistry.reader, which pulls the image at deploy time." "IAM service account"

                cloudRunNode = deploymentNode "Cloud Run" "Scales to zero, at most two instances." "Cloud Run" {
                    cloudRunInstance = containerInstance cloudRun
                }

                firestoreNode = deploymentNode "Firestore" "The named database invoices, in the project region." "Cloud Firestore" {
                    firestoreInstance = containerInstance firestore
                }

                archiveNode = deploymentNode "Cloud Storage" "One bucket, uniform access, objects deleted after seven days." "Cloud Storage" {
                    archiveInstance = containerInstance archive
                }
            }

            vertexNode = deploymentNode "Vertex AI" "Outside the project boundary in the sense that matters here: nobody deploys it." "Google Cloud" {
                geminiInstance = softwareSystemInstance gemini
            }

            cloudRunInstance -> serviceAccount "Runs as"
            serviceAccount -> geminiInstance "roles/aiplatform.user"
            serviceAccount -> firestoreInstance "roles/datastore.user"
            serviceAccount -> archiveInstance "roles/storage.objectUser"
        }
    }

    views {
        systemContext deployedService "SystemContext" {
            include *
            include attendee
            autoLayout lr
            description "What an attendee reaches, and what it reaches out to. The Origin shim is outside the boundary: it runs on a laptop, not in the project. Vertex AI Gemini is outside it because nobody deploys the model."
        }

        container deployedService "Containers" {
            include *
            autoLayout lr
            description "What the first Terraform apply put in the project. One container, because the agent runs in-process inside the FastAPI application and is not deployed on its own. The Artifact Registry repository the image is pushed to is build-time only, so it is named here and not drawn."
        }

        component cloudRun "Components" {
            include *
            autoLayout lr
            description "Everything inside the one container, and two facts prose has to work hard to say. Both the arithmetic tool and the save tool call the same validation chain, which is why the store's answer is trustworthy and the agent's claim is not. And the document guard sits between the agent and the model, not in front of the endpoint. The Pydantic models are types, so they are named on the arrows rather than drawn as boxes."
        }

        dynamic cloudRun "RiggedInvoice" {
            originShim -> uploadPage "The browser posts the rigged invoice, one document"
            uploadPage -> invoiceAnalyzer "Drives one run, document bytes attached"
            invoiceAnalyzer -> documentGuard "Every turn goes through the guard first"
            documentGuard -> gemini "Bytes are attached, so the turn reaches the model"
            invoiceAnalyzer -> arithmeticTool "First check, with the reading off the document"
            arithmeticTool -> validation "The lines do not sum to the printed total: ok=false"
            invoiceAnalyzer -> documentGuard "The re-read: back to the document for what the first pass missed"
            documentGuard -> gemini "The second look at the same bytes"
            invoiceAnalyzer -> arithmeticTool "Second check, even though nothing changed"
            arithmeticTool -> validation "Still ok=false: the invoice itself does not add up"
            invoiceAnalyzer -> lookupTool "Resolves the supplier name as printed"
            lookupTool -> supplierRegistry "Matches it through the aliases"
            invoiceAnalyzer -> saveTool "Files the record, discrepancy included"
            saveTool -> validation "Validation runs again; the store decides validation_passed"
            saveTool -> store "Hands over the InvoiceRecord and the document bytes"
            store -> firestore "Writes the record"
            store -> archive "Copies the analysed document"
            autoLayout lr
            description "The rigged invoice, end to end, without waiting for a run. Step 9 is the one the hour is built around: the arithmetic check called a second time after the re-read at step 7, even though the second look changed nothing. Steps 11 to 17 are what happens next, which is that an invoice that does not add up is filed anyway, flagged. There is no happy-path version of this view."
        }

        deployment deployedService "Attendee project" "Deployment" {
            include *
            autoLayout lr
            description "What runs where, and as whom. What this adds over the container view is the identity: one service account the stack owns, and the four role bindings Terraform grants it. Artifact Registry is still not drawn; the binding that pulls the image is named on the account."
        }

        # Vendored rather than referenced by URL, so the export runs with no
        # network access. Only the icons the model uses are committed beside it.
        theme "google-cloud-theme.json"

        styles {
            element "Person" {
                shape person
            }
            element "External" {
                background "#8a8a8a"
                color "#ffffff"
            }
        }
    }
}
