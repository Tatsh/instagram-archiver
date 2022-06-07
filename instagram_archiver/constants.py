from typing import Final, Mapping

__all__ = ('EXTRACT_VIDEO_INFO_JS', 'EXTRACT_XIGSHAREDDATA_JS',
           'SHARED_HEADERS', 'USER_AGENT')

USER_AGENT: Final[str] = ('Mozilla/5.0 (X11; Linux x86_64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/103.0.0.0 Safari/537.36')
SHARED_HEADERS: Final[Mapping[str, str]] = {
    'accept':
    ('text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,'
     'image/avif,image/webp,image/apng,*/*;q=0.8,'
     'application/signed-exchange;v=b3;q=0.9'),
    'accept-language':
    'en,en-GB;q=0.9,en-US;q=0.8',
    'authority':
    'www.instagram.com',
    'cache-control':
    'no-cache',
    'dnt':
    '1',
    'pragma':
    'no-cache',
    'referer':
    'https://www.instagram.com',
    'upgrade-insecure-requests':
    '1',
    'user-agent':
    USER_AGENT,
    'viewport-width':
    '2560',
    'x-ig-app-id':
    '936619743392459'
}
EXTRACT_XIGSHAREDDATA_JS: Final[str] = '''const qpl_inl = () => {};
class ServerJS {
  handleWithCustomApplyEach(x, z) {
    for (x of z.define) {
      if (x[0] === 'XIGSharedData') {
        console.log(JSON.stringify(x[2].native, null, 2));
      }
    }
  }
}
const requireLazy = (a, b) => {
  b({ runWithPriority: (_, cb) => cb() }, ServerJS, () => {});
};'''
EXTRACT_VIDEO_INFO_JS: Final[str] = '''const qpl_inl = () => {};
class ServerJS {
  handleWithCustomApplyEach(x, z) {
    for (x of z.require) {
      if (x[0] === 'CometPlatformRootClient') {
        console.log(JSON.stringify(x[3][3], null, 2));
      }
    }
  }
}
const requireLazy = (a, b) => {
  b({ runWithPriority: (_, cb) => cb() }, ServerJS, () => {});
};'''
