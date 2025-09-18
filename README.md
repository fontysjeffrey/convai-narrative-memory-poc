# IxD Research Project Template

A clean, modern, and mobile-friendly template for creating academic project pages and fostering collaborative research. This template is maintained by the [Fontys University of Applied Sciences' Interaction Design (IxD) Research Group](https://www.ixdfontysict.nl) to help students and researchers showcase their work effectively and collaborate efficiently.

## Getting Started: Repository Setup

To ensure the integrity of the research project and a smooth collaboration process, please follow these initial setup steps carefully after creating a repository from this template.

### 1. Create a `dev` Branch

All ongoing work, feature additions, and experiments should happen in a `dev` branch. The `main` branch should reflect the stable, reviewed state of the project.

Create the `dev` branch from `main`:

```bash
git checkout -b dev
git push -u origin dev
```

### 2. Protect the `main` Branch

To prevent accidental pushes and ensure all changes to the `main` branch are reviewed, you must protect it. This is a critical step.

To enforce branch protection for the `main` branch:

1.  Navigate to your repository's main page on GitHub.
2.  Click the **Settings** tab.
3.  In the "Code and automation" section of the sidebar, click **Branches**.
4.  Under "Branch protection rules," click **Add rule**.
5.  Enter `main` in the "Branch name pattern" field.
6.  Configure the desired protection settings. It is highly recommended to:
    - Enable "**Require a pull request before merging**".
    - Enable "**Require approvals**".
7.  Click **Create** to save the rule.

## Contribution Workflow for External Collaborators

For students and researchers outside of the core project organization, collaboration is managed through forks and pull requests. This ensures that all contributions are reviewed before being integrated.

1.  **Fork the Repository:** Create your own copy of the repository by clicking the "Fork" button on the top-right of the repository page.
2.  **Clone Your Fork:** Clone your forked repository to your local machine.
    ```bash
    git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
    ```
3.  **Create a Feature Branch:** Create a new branch on your local machine to work on your feature or bug fix.
    ```bash
    git checkout -b my-awesome-feature
    ```
4.  **Make Your Changes:** Edit the code, add your research, and commit your changes.
5.  **Push to Your Fork:** Push your feature branch to your forked repository on GitHub.
    ```bash
    git push -u origin my-awesome-feature
    ```
6.  **Create a Pull Request (PR):** Navigate to the original repository and you will see a prompt to create a pull request from your new branch. Ensure your PR is targeted to merge into the `dev` branch of the upstream (original) repository. Provide a clear title and description for your contribution.

## Project Management Methodology

This project adheres to the **Project-Driven Creation (PMC)** methodology, a framework that balances the structured aspects of project management with a focus on leadership, collaboration, and stakeholder engagement. For a detailed guide on how we apply PMC in this project, please see our comprehensive guide:

- [A Comprehensive Guide to Project Planning with Project-Driven Creation (PMC)](docs/project-driven-creation-PMC.md)

## Project Page Customization

This template also includes a pre-built academic project page.

### Features

- **Teaser Video:** A prominent video banner to showcase your project's main outcome.
- **Image & Video Carousels:** Display multiple images and videos in a clean, interactive format.
- **Embedded Content:** Easily embed YouTube videos and PDF posters.
- **BibTeX Citation:** A pre-formatted BibTeX entry to make it easy for others to cite your work.
- **Responsive Design:** Looks great on desktops, tablets, and mobile devices.

### Customization Checklist

To ensure your project page is complete, make sure you update the following in `docs/index.html`:

- [ ] **Metadata:** Fill in the `<meta>` tags in the `<head>` section for SEO and social media previews.
- [ ] **Title & Authors:** Update the project title and author information.
- [ ] **Links:** Replace all placeholder links with your actual URLs (Paper, Code, Supplementary materials, etc.).
- [ ] **Abstract:** Write a compelling abstract for your project.
- [ ] **Visuals:** Replace all placeholder images and videos in the `docs/static/` directory with your own.
- [ ] **BibTeX Citation:** Update the BibTeX entry with your author details and the final URL of your project page.
- [ ] **Favicon:** Replace the default `favicon.ico` in `docs/` with your own icon.

## Acknowledgements

This template was adapted from the [Academic Project Page Template](https://github.com/eliahuhorwitz/Academic-project-page-template) by Eliahu Horwitz, which was in turn inspired by the [Nerfies](https://nerfies.github.io/) project page.

## License

This work is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](http://creativecommons.org/licenses/by-sa/4.0/). You are free to use and adapt this template, but we kindly ask that you provide attribution by linking back to this repository in your site's footer.
