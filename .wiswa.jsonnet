local utils = import 'utils.libjsonnet';

(import 'defaults.libjsonnet') + {
  // Project-specific
  description: 'Save Instagram content you have access to.',
  keywords: ['command line', 'instagram'],
  project_name: 'instagram-archiver',
  version: '0.3.0',
  want_main: true,
  supported_python_versions: ['3.%d' % i for i in std.range(12, 13)],
  citation+: {
    'date-released': '2025-05-10',
  },
  pyproject+: {
    project+: {
      scripts: {
        'instagram-archiver': 'instagram_archiver.main:main',
        'instagram-save-saved': 'instagram_archiver.main:save_saved_main',
      },
    },
    tool+: {
      poetry+: {
        dependencies+: {
          requests: '^2.32.3',
          'yt-dlp-utils': '^0',
        },
        group+: {
          dev+: {
            dependencies+: {
              'types-requests': '^2.31.0.20240106',
            },
          },
        },
      },
    },
  },
  // Common
  authors: [
    {
      'family-names': 'Udvare',
      'given-names': 'Andrew',
      email: 'audvare@gmail.com',
      name: '%s %s' % [self['given-names'], self['family-names']],
    },
  ],
  local funding_name = '%s2' % std.asciiLower(self.github_username),
  github_username: 'Tatsh',
  github+: {
    funding+: {
      ko_fi: funding_name,
      liberapay: funding_name,
      patreon: funding_name,
    },
  },
}
