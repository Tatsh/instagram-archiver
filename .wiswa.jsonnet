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
          requests: utils.latestPypiPackageVersionCaret('requests'),
          'yt-dlp-utils': utils.latestPypiPackageVersionCaret('yt-dlp-utils'),
        },
        group+: {
          dev+: {
            dependencies+: {
              'types-requests': utils.latestPypiPackageVersionCaret('types-requests'),
            },
          },
        },
      },
    },
  },
}
