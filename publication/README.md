# Publication and persistent identifiers

The publication workflow produces a static RDF distribution at <https://rgu-computing.github.io/icareonto/>. The ontology and entity namespace remains <https://w3id.org/icareonto/>. Deployment changes the documents to which those identifiers resolve; it does not rename the entities.

## One-time setup

1. Commit the publishing script, its tests, this directory and `.github/workflows/publish.yml` to the default branch.
2. In GitHub repository **Settings → Pages → Build and deployment**, select **GitHub Actions** as the source. Organisation policy must permit the official GitHub Actions used by the workflow and its `contents: write` permission to maintain the publication branch.
3. In **Actions → Publish ontology and educational catalogue**, select **Run workflow** on the default branch and tick **Create the publication branch (first deployment only)**. Leave this unchecked on later runs; the workflow then refuses to recreate a missing publication history silently.
4. Confirm a successful deployment and the documents listed in `publication.json`. Check the live root Turtle/RDF/XML content types and online imports before requesting the w3id redirect.
5. Copy the two files in `publication/w3id/` into `ids/icareonto/` in the w3id fork, run its contribution checks, and submit that identifier directory to `perma-id/w3id.org`. The redirect targets must already be live.

The `gh-pages` branch is created and maintained by the workflow. It stores only the public distribution and preserved snapshots. GitHub Pages is deployed with the official Pages Actions; the branch provides durable release history between builds, rather than acting as the configured Pages build source.

Use the manual workflow for the initial deployment from the committed default branch. The existing `v1.0.0` tag predates namespace finalisation; it must identify the intended namespace-finalised source before being used to publish a GitHub Release.

After deployment the workflow runs `scripts/check_publication_site.py`. It checks live media types, equivalent Turtle/RDF/XML exports and the current and archived ontology/catalogue import closures independently of w3id. A hosting response with an incorrect RDF media type causes the check to fail and must be resolved before the w3id request.

## What gets published

```text
current/                         Current ontology documents
  ontology.ttl                   Complete, self-contained ontology
  ontology.rdf                   Equivalent RDF/XML
  icareonto.ttl                   Modular entry point
  <module>.ttl                   Module documents
  imports/                       Reference subsets
releases/<version>/              Preserved ontology snapshots
education/current/               Current educational metadata in RDF and JSON
education/releases/<release-id>/ Preserved educational metadata snapshots
publication.json                 Active versions and source commit
index.html                       Access and licensing links
```

The complete ontology document combines the imported axioms under a single ontology header. It includes term definitions directly, so a term IRI resolves to useful RDF without requiring a client to follow imports. Individual module documents remain available. The Turtle and RDF/XML exports express the same graph.

Archived ontology imports point to that ontology version. Archived educational imports point to the associated ontology version and catalogue snapshot. Current documents retain the stable current imports. The web distribution has its own manifests and is not the Education Resource Selector's operational loader package; use `education/data/catalogue/` in the source repository with that tool. Provider publications, participant records, source workbooks, caches and test data are not copied into the website.

## Publish a subsequent release

1. Update the source workbooks and regenerate the affected package assets. For an ontology change, set the new ontology version and refresh dependent catalogue assets and validation evidence.
2. Run the package checks and review the changes. Commit them to the default branch.
3. Publish using **Run workflow**. Publishing a GitHub Release also runs the workflow against its tag; that tag must be `v` followed by the ontology version and must reference the intended source commit. Catalogue-only updates can be published manually without changing the ontology version.

The builder loads the existing `gh-pages` distribution, validates its archived hashes, adds new release directories, and refreshes the current documents. Existing release directories are retained byte-for-byte. Changed content under an already published ontology version or catalogue identifier is rejected; publish a new identity instead. An older ontology version cannot replace the current version. Ordinary commits do not deploy the site.

Do not delete or force-replace `gh-pages`: it contains the preserved snapshots that later builds must retain. The workflow pushes normally, so an unexpected concurrent branch change causes a failure rather than overwriting it. If deployment fails after the branch was saved, rerun the workflow; previously saved snapshots remain available to the builder.

Routine versions, catalogue additions and new modules require no w3id rule edits with this path layout. A hosting-address change or new identifier-path convention still requires a w3id update.

## Local inspection and checks

```bash
python -m unittest discover -s scripts/tests -v
python scripts/build_publication.py --output build/site
```

`build/` is ignored. The output directory must not already exist. For a subsequent local build, provide the previous site explicitly and choose a new output directory:

```bash
python scripts/build_publication.py --previous build/site --output build/next-site
```

Do not omit `--previous` when rebuilding an established publication: the first-build mode has no historical snapshots to preserve. The GitHub workflow supplies the previous distribution automatically whenever the branch exists.

After deployment, verify the real hosting response rather than relying on local file checks:

```bash
curl -I https://rgu-computing.github.io/icareonto/current/ontology.ttl
curl -I https://rgu-computing.github.io/icareonto/current/ontology.rdf
python scripts/check_publication_site.py
```

The expected media types are `text/turtle` and `application/rdf+xml`. Verify that a clean RDF client can load the modular ontology and preserved educational dataset through their w3id IRIs once the redirects are deployed. The local redirect tests do not establish that the production service has deployed the configuration.

GitHub reference: [Publishing with custom GitHub Actions workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages). w3id reference: [Creating an identifier](https://github.com/perma-id/w3id.org/blob/master/docs/guides/create-an-id.md).
