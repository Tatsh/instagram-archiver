local utils = import 'utils.libjsonnet';

{
  uses_user_defaults: true,
  description: 'Save Instagram content you have access to.',
  keywords: ['command line', 'instagram'],
  project_name: 'instagram-archiver',
  version: '0.3.5',
  want_main: true,
  want_flatpak: true,
  publishing+: { flathub: 'sh.tat.instagram-archiver' },
  security_policy_supported_versions: { '0.3.x': ':white_check_mark:' },
  docs_conf+: {
    config+: {
      intersphinx_mapping+: {
        'archiver-stats': ['https://archiver-stats.readthedocs.io/en/latest/', null],
        rich: ['https://rich.readthedocs.io/en/stable/', null],
      },
    },
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
          anyio: utils.latestPypiPackageVersionCaret('anyio'),
          'archiver-stats': utils.latestPypiPackageVersionCaret('archiver-stats'),
          niquests: utils.latestPypiPackageVersionCaret('niquests'),
          rich: utils.latestPypiPackageVersionCaret('rich'),
          'yt-dlp-utils': {
            extras: ['asyncio'],
            version: utils.latestPypiPackageVersionCaret('yt-dlp-utils'),
          },
        },
        group+: {
          tests+: {
            dependencies+: {
              'pytest-asyncio': utils.latestPypiPackageVersionCaret('pytest-asyncio'),
            },
          },
        },
      },
      pytest+: {
        ini_options+: {
          asyncio_default_fixture_loop_scope: 'function',
          asyncio_mode: 'auto',
        },
      },
      uv+: {
        'exclude-newer-package'+: {
          'archiver-stats': false,
          'yt-dlp-utils': false,
        },
      },
    },
  },
  tests_pyproject+: {
    tool+: {
      ruff+: {
        lint+: {
          'extend-ignore'+: ['RUF029'],
        },
      },
    },
  },
  readthedocs+: {
    sphinx+: {
      fail_on_warning: false,
    },
  },
}
