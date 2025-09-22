local utils = import 'utils.libjsonnet';

{
  description: 'Save Instagram content you have access to.',
  keywords: ['command line', 'instagram'],
  project_name: 'instagram-archiver',
  version: '0.3.2',
  want_main: true,
  security_policy_supported_versions: { '0.3.x': ':white_check_mark:' },
  supported_python_versions: ['3.%d' % i for i in std.range(12, 13)],
  copilot: {
    intro: 'Instagram Archiver is a command line tool to save Instagram content you have access to.',
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
