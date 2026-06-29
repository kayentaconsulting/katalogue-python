// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://kayentaconsulting.github.io/katalogue-python/',
  base: '/katalogue-python',
  integrations: [
    starlight({
      title: 'Katalogue SDK & CLI',
      social: [
        {
          icon: 'github',
          label: 'GitHub',
          href: 'https://github.com/kayentaconsulting/katalogue-python',
        },
      ],
      logo: {
        light: './src/assets/logo-light.svg',
        dark: './src/assets/logo-dark.svg',
        replacesTitle: true,
        alt: 'Katalogue SDK & CLI',
      },
      head: [
        {
          tag: 'link',
          attrs: { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        },
        {
          tag: 'link',
          attrs: { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        },
        {
          tag: 'link',
          attrs: {
            rel: 'stylesheet',
            href: 'https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;700&display=swap',
          },
        },
      ],
      customCss: ['./src/styles/custom.css'],
      sidebar: [
        { label: 'Getting started', link: '/getting-started' },
        {
          label: 'CLI',
          items: [
            { label: 'Commands', link: '/cli/commands' },
            { label: 'Output & file output', link: '/cli/output-formats' },
          ],
        },
        {
          label: 'SDK',
          items: [
            { label: 'Client & authentication', link: '/sdk/client' },
            { label: 'Options & results', link: '/sdk/options' },
          ],
        },
        {
          label: 'Guides',
          items: [
            { label: 'Exporting hierarchies', link: '/guides/exporting' },
            { label: 'Templates', link: '/guides/templates' },
            { label: 'Datatype conversion', link: '/guides/datatype-conversion' },
          ],
        },
        {
          label: 'Reference',
          items: [
            { label: 'Filtering & selection', link: '/reference/filtering' },
            { label: 'Resources', link: '/reference/resources' },
            { label: 'Troubleshooting', link: '/reference/troubleshooting' },
          ],
        },
        {
          label: 'Maintainers',
          items: [{ label: 'Publishing to PyPI', link: '/maintainers/publishing' }],
        },
      ],
    }),
  ],
});
