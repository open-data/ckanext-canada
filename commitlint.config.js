const Configuration = {
  /*
   * Resolve and load @commitlint/config-conventional from node_modules.
   * Referenced packages must be installed
   */
  extends: ['@commitlint/config-conventional'],
  /*
   * Any rules defined here will override rules from @commitlint/config-conventional
   * See https://commitlint.js.org/#/reference-rules?id=available-rules
   * Rules are defined as lists:
   *  - level(int:required): 0 disabled, 1 warning, 2 error
   *  - behaviour(string:required): 'always', 'never'
   *  - value(mixed:optional): value to match
   */
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'build',
        'chore',
        'ci',
        'docs',
        'feat',
        'fix',
        'perf',
        'refactor',
        'revert',
        'style',
        'test',
        'misc',
        'merge',
        'cherry-pick',
      ]
    ],
    'scope-empty': [
      2,
      'never',
    ],
    'scope-enum': [
      2,
      'always',
      [
        'templates',
        'controllers',
        'views',
        'plugins',
        'users',
        'resources',
        'api',
        'commands',
        'gitflow',
        'dev',
        'tests',
      ]
    ],
    'subject-full-stop': [
      0,
    ],
    'header-full-stop': [
      2,
      'always',
      ';',
    ],
    'body-empty': [
      0,
      'never',
    ],
    'body-leading-blank': [
      2,
      'always',
    ],
    'body-full-stop': [
      2,
      'always',
      '.',
    ],
    'body-starts-with': [
      2,
      'always',
      '- '
    ],
  },
  /*
   * Custom plugins
   */
  plugins: [
    {
      rules: {
        'header-full-stop': (parsed, behaviour, value) => {
          if ( ! parsed.header ){ return [true, ''] }
          return [parsed.header.endsWith(value), 'header must end with `' + value + '`']
        },
        'body-full-stop': (parsed, behaviour, value) => {
          if ( ! parsed.body ){ return [true, ''] }
          return [parsed.body.endsWith(value), 'body must end with `' + value + '`']
        },
        'body-starts-with': (parsed, behaviour, value) => {
          if ( ! parsed.body ){ return [true, ''] }
          return [parsed.body.startsWith(value), 'body must start with `' + value + '`']
        },
      },
    },
  ],
}

module.exports = Configuration;
