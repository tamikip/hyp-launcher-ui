/* ============================================================
   全部可自定义内容都在这个文件里。
   结构与命名对齐官方前端（左侧 .hyp-side-bar / 右侧 .hyp-game-social-media /
   页面 .app-container），几何数值见 css/tokens.css。
   ============================================================ */

window.HOYO_CONFIG = {
  /* ---------- 应用信息 ---------- */
  app: {
    name: '示例启动器',
    /* 启动后默认进入的游戏，设为 null 则进入 Hub 页 */
    primaryGame: 'c01_cn',
  },

  /* ---------- 左侧侧栏 ----------
     官方 .hyp-side-bar：顶部 logo，底部是"已安装游戏"图标列表（36x36）+ 分隔线 +
     添加游戏按钮。这里只放你想要显示的条目，顺序即显示顺序。
  ---------------------------------- */
  sidebar: {
    /* 官方侧栏 logo 是 CSS 内联的 44x44 SVG（fill:#fff + 投影滤镜），
       已从真实 CSS 里提取，直接用它就与官方像素一致 */
    logo: 'assets/icons/logo-app.svg',
    /* 官方只列出【已安装】的游戏。这里默认与官方当前状态一致（只装了星铁，
       且它正处于"下载中"，所以官方那颗图标上盖了深色蒙层并带黄色下载角标）。
       要加更多游戏就在数组里加条目，会自动往下堆叠。
       state: 'downloading' 会加官方那层 rgba(13,13,15,.6) 蒙层 + 黄色角标
       （实测：官方该处像素 (103,104,105) = 原图 250 压 60% 后的结果） */
    games: [
      {
        key: 'c01_cn',
        name: '示例游戏 A',
        icon: 'assets/icons/icon-c01.png',
        state: 'downloading',
      },
    ],
    /* 添加游戏按钮的红点（官方当前没有，默认关） */
    addGameBadge: false,
  },

  /* ---------- 右侧社交栏 ----------
     官方 .hyp-game-social-media：9 项，每项 44x44，图标 36x36。
     图标是从官方界面 1:1 抠出的白色图形（带 alpha）。
     action 填网址则点击用系统浏览器打开；不填则弹出提示。
  ---------------------------------- */
  social: [
    { icon: 'social-01', label: '官方社区' },
    { icon: 'social-02', label: '消息' },
    { icon: 'social-03', label: '米游社' },
    { icon: 'social-04', label: '微博' },
    { icon: 'social-05', label: '攻略' },
    { icon: 'social-06', label: '账号', popup: 'account' },
    { icon: 'social-07', label: '帮助' },
    { icon: 'social-08', label: '在线客服' },
    /* 官方第 9 项是内联 data-URI 图标，已导出（社交栏共 9 项，pitch 56） */
    { icon: 'social-inline-14', label: '更多' },
  ],

  /* ---------- 窗口控制 ---------- */
  windowControls: ['settings', 'minimize', 'close'],

  /* ---------- 游戏（启动页）----------
     background     全屏背景（官方 2560x1440，精确铺满 1280x720）
     titleOverlay   叠加在背景上的透明层（含游戏 logo 与版本标题）
     chip           版本热点雪碧图（270x80，按 height:40px 显示为 135 宽）
     carousel       活动轮播图，每项 { img, href }
     news           按页签分组 { activity:[], notice:[], info:[] }
     cta            主按钮 { text }
     installed      是否已安装（true 时按钮变成"开始游戏"）
     progress       底部进度文字，null 表示不显示
  ---------------------------------- */
  games: {
    c01_cn: {
      name: '示例游戏 A',
      /* 说明：底图 21__f5e11e5c...webp 自带版本标题，
         与官方渲染在左上/右上/中部差异为 9.0 / 20.3 / 1.6（满分 255） */
      background: 'assets/img/bg-canghai.webp',
      /* 官方该状态不需要额外标题叠层（标题已烧在底图里），设 null */
      titleOverlay: 'assets/img/overlay-launcher-title.webp',
      /* 暗角遮罩：对官方渲染逐区域解 k=<素材·官方>/<素材·素材> 拟合出的二维暗化场
         （右边缘上暗→中亮→下暗，左边缘上亮→下暗），导出为等尺寸 PNG。
         它已包含底部渐变，所以 scrim 显式关掉，避免重复压暗。 */
      vignette: 'assets/img/bg-vignette.png',
      scrim: false,
      /* 背景切换器（官方 #hyp-background-switcher）：>=2 项时顶部居中出圆点 */
      backgrounds: [
        { name: '夜色 一', art: 'assets/img/bg-canghai.webp', vignette: 'assets/img/bg-vignette.png' },
        { name: '夜色 二', art: 'assets/img/bg-launcher-c01.webp' },
        { name: 'Hub 背景', art: 'assets/img/bg-hub-official.webp' },
        { name: '动态背景', art: 'assets/img/bg-canghai.webp',
          video: 'assets/img/bg-anim.webm', vignette: 'assets/img/bg-vignette.png' },
      ],
      /* 区服切换（官方 .hyp-server-switcher） */
      servers: [
        { key: 'cn', name: '正式服', tag: 'Stable' },
        { key: 'os', name: '测试服', tag: 'Beta' },
        { key: 'bili', name: '预发布', tag: 'Canary' },
      ],
      /* 官方当前状态没有播放/暂停按钮（有背景视频时才出现） */
      pause: false,
      /* 官方实测：主按钮黄底与按钮内箭头同为 #ffdb29，深色文字 #16171a */
      accent: '#4ea1ff',
      accentInk: '#0d1420',
      /* 官方 chip 是 2x 图（270x80 -> 显示 135x40）：查看活动 / 版本热点两套 */
      /* chip 是两张图：常态（白底）+ 悬停（灰底），悬停时上滚切换 */
      chip: {
        normal: 'assets/img/chip-activity.png',
        hover: 'assets/img/chip-activity-hover.png',
      },
      carousel: [
        { img: 'assets/img/card-banner-5.png', href: '#' },
        { img: 'assets/img/card-banner-6.jpg', href: '#' },
        { img: 'assets/img/card-banner-7.png', href: '#' },
        { img: 'assets/img/card-banner-8.jpg', href: '#' },
        { img: 'assets/img/card-banner-9.png', href: '#' },
        { img: 'assets/img/card-banner-10.png', href: '#' },
        { img: 'assets/img/card-banner-11.png', href: '#' },
      ],
      news: {
        activity: [
          { title: '示例活动：分享页面赢取周边', date: '09/28', href: '#' },
          { title: '示例征集活动现已开启', date: '09/23', href: '#' },
        ],
        notice: [
          { title: '关于若干已知问题的修复说明', date: '09/30', href: '#' },
          { title: '9 月 30 日版本更新维护公告', date: '09/29', href: '#' },
        ],
        info: [
          { title: '示例角色前瞻与技能解析', date: '09/27', href: '#' },
          { title: '新版本内容一览', date: '09/25', href: '#' },
        ],
      },
      cta: { text: '获取游戏', launchText: '开始游戏' },
      installed: false,
      /* 下载/更新用的字段：
         size      完整包大小（GB），未安装时点按钮按这个下载
         patchSize 增量包大小（GB），updateTo 非空时走增量
         version   当前版本；updateTo 非空表示有可用更新
         progress  底部那行静态文字（有真实任务时会被实时进度覆盖） */
      size: 12.6,
      patchSize: 1.8,
      version: '1.18.2',
      updateTo: null,
      progress: { text: '剩余文件', done: '4.8', total: '12.6' },
    },

    c07_cn: {
      name: '示例游戏 B',
      background: 'assets/img/bg-hub-alt5.webp',
      titleOverlay: 'assets/img/overlay-launcher-title.webp',
      accent: '#7ee0c0',
      /* chip 是两张图：常态（白底）+ 悬停（灰底），悬停时上滚切换 */
      chip: {
        normal: 'assets/img/chip-activity.png',
        hover: 'assets/img/chip-activity-hover.png',
      },
      carousel: [
        { img: 'assets/img/card-banner-6.jpg', href: '#' },
        { img: 'assets/img/card-banner-7.png', href: '#' },
      ],
      news: {
        activity: [{ title: '版本主题活动开启（示例）', date: '09/24', href: '#' }],
        notice: [{ title: '版本更新维护公告', date: '09/23', href: '#' }],
        info: [{ title: '新内容前瞻（示例）', date: '09/22', href: '#' }],
      },
      cta: { text: '获取游戏', launchText: '开始游戏' },
      installed: true,
      size: 24.5,
      patchSize: 2.4,
      version: '4.6.0',
      /* 演示「有可用更新」：非空时按钮走 update 分支，侧栏图标挂下载角标 */
      updateTo: '4.7.0',
      progress: null,
    },
  },

  /* ---------- Hub 游戏选择页 ----------
     官方 .hub-page：落地 logo(68,40 210x160) + 简介 + 卡片行(左128 底664)
     entries 里：
       name        卡片下方游戏名
       card        卡片图（官方 124x124 正方形，object-fit: cover）
       art         源 key art，供自己合成卡片时用
       logoOverlay 该游戏卡片的 logo 透明叠层（416x234 RGBA）
       reserve     true 显示"预约"角标
       page        点击后进入 games 里的哪个启动页；没有则仅切换选中
       landLogo    切换该游戏时左上角落地 logo
       description 切换该游戏时的简介
  ---------------------------------- */
  hub: {
    background: 'assets/img/bg-hub-official.webp',
    /* 背景之上的黑色遮罩不透明度（官方拟合值 0.221） */
    bgDim: 0.221,
    logo: 'assets/icons/hub-land-logo-c01.png',
    description:
      '这是一个用于演示的示例游戏简介。\n' +
      '你将登上星穹列车造访寓居宇宙的万象世界，携手形形色色的旅伴解\n' +
      '救「星核」引发的种种危机，对抗「星神」践踏文明的意图。',
    entries: [
      {
        key: 'c01_cn',
        name: '示例游戏 A',
        card: 'assets/img/hub/card-c01.png',
        art: 'assets/img/hub/art-c01.png',
        logoOverlay: 'assets/img/hub/logo-c01.png',
        landLogo: 'assets/icons/hub-land-logo-c01.png',
        page: 'c01_cn',
      },
      {
        key: 'c03',
        name: '星布谷地',
        card: 'assets/img/hub/card-c03.png',
        art: 'assets/img/hub/art-c03.jpg',
        reserve: true,
      },
      {
        key: 'c02',
        name: '示例游戏 C',
        card: 'assets/img/hub/card-c02.png',
        art: 'assets/img/hub/art-c02.jpg',
        logoOverlay: 'assets/img/hub/logo-overlay-c02.png',
        landLogo: 'assets/icons/hub-land-logo-c10.png',
        reserve: true,
      },
      {
        key: 'c06_cn',
        name: '示例游戏 E',
        card: 'assets/img/hub/card-c06.png',
        art: 'assets/img/hub/art-c06.jpg',
        landLogo: 'assets/icons/hub-land-logo-c09.png',
      },
      {
        key: 'c07_cn',
        name: '示例游戏 B',
        card: 'assets/img/hub/card-c05.png',
        art: 'assets/img/hub/art-c05.png',
        logoOverlay: 'assets/img/hub/logo-c07.png',
        landLogo: 'assets/icons/hub-land-logo-c07.png',
        page: 'c07_cn',
      },
      {
        key: 'c08_cn',
        name: '示例游戏 D',
        card: 'assets/img/hub/card-c04.png',
        art: 'assets/img/hub/art-c04.png',
        logoOverlay: 'assets/img/hub/logo-c08.png',
        landLogo: 'assets/icons/hub-land-logo-c08.png',
      },
    ],
  },

  /* ---------- 多语言 ----------
     key 就是界面文案的查找键；没配到的语言会回退到 zh-CN。
     切换语言由设置里的 lang 项驱动（见 app.js 的 applyLocalSettings）。 */
  locales: {
    'zh-CN': {
      'task.downloading': '正在下载 ',
      'task.updating': '正在更新 ',
      'task.paused': '已暂停',
      'task.retry': '重试',
      'task.install': '安装',
      'task.queuedShort': '排队中',
      'task.queued': '已加入队列，等前面的下载完成',
      'task.preStarted': '已加入预下载，完成后可手动安装',
      'task.preDone': '预下载完成，可以安装了',
      'phase.verifying': '校验中',
      'phase.extracting': '解压中',
      'phase.installing': '安装中',
      'phase.ready': '待安装',
      'menu.launch': '启动游戏',
      'menu.locate': '打开安装目录',
      'menu.verify': '校验文件完整性',
      'menu.uninstall': '卸载',
      'menu.download': '下载',
      'menu.pre': '预下载',
      'menu.launched': '已请求启动',
      'menu.verifying': '开始校验文件…',
      'uninstall.title': '卸载',
      'uninstall.ask': '确定要卸载 ',
      'uninstall.note': '卸载会删除游戏文件，存档默认保留（由宿主决定）。',
      'uninstall.ok': '卸载',
      'uninstall.done': '已卸载',
      'common.cancel': '取消',
      'common.tip': '提示',
      'account.guest': '未登录',
      'account.switch': '切换账号',
      'account.logout': '退出登录',
      'account.settings': '设置',
      'account.quit': '退出启动器',
      'account.quitSent': '已请求退出（需宿主接管）',
      'account.switchSent': '请在宿主里完成账号切换',
      'account.logoutSent': '已请求退出登录',
      'social.opening': '正在用浏览器打开',
      'social.todo': '这里可以接你自己的页面或宿主功能。',
      'social.hint': '在 config 里给这一项加 action 或 panel 字段即可生效。',
      'bg.switched': '已切换背景',
      'server.switched': '已切换到 ',
      'win.needHost': '窗口控制需要宿主 exe（浏览器里不可用）',
    },
    en: {
      'task.downloading': 'Downloading ',
      'task.updating': 'Updating ',
      'task.paused': 'Paused',
      'task.retry': 'Retry',
      'task.install': 'Install',
      'task.queuedShort': 'Queued',
      'task.queued': 'Queued — will start when a slot frees up',
      'task.preStarted': 'Pre-download started; install manually when done',
      'task.preDone': 'Pre-download complete, ready to install',
      'phase.verifying': 'Verifying',
      'phase.extracting': 'Extracting',
      'phase.installing': 'Installing',
      'phase.ready': 'Ready',
      'menu.launch': 'Launch',
      'menu.locate': 'Open folder',
      'menu.verify': 'Verify files',
      'menu.uninstall': 'Uninstall',
      'menu.download': 'Download',
      'menu.pre': 'Pre-download',
      'menu.launched': 'Launch requested',
      'menu.verifying': 'Verifying files…',
      'uninstall.title': 'Uninstall',
      'uninstall.ask': 'Uninstall ',
      'uninstall.note': 'Game files will be removed; saves are kept (host decides).',
      'uninstall.ok': 'Uninstall',
      'uninstall.done': 'Uninstalled',
      'common.cancel': 'Cancel',
      'common.tip': 'Notice',
      'account.guest': 'Not signed in',
      'account.switch': 'Switch account',
      'account.logout': 'Sign out',
      'account.settings': 'Settings',
      'account.quit': 'Quit launcher',
      'account.quitSent': 'Quit requested (host must handle)',
      'account.switchSent': 'Complete sign-in in the host',
      'account.logoutSent': 'Sign-out requested',
      'social.opening': 'Opening in browser: ',
      'social.todo': 'Hook your own page or host feature here.',
      'social.hint': 'Add an action or panel field to this item in config.',
      'bg.switched': 'Background: ',
      'server.switched': 'Switched to ',
      'win.needHost': 'Window controls need the host exe (unavailable in a browser)',
    },
  },

  /* ---------- 账号 ---------- */
  account: {
    avatar: 'assets/icons/logo-app.svg',
    nick: 'Tamiki',
    uid: 'UID 100000000',
  },

  /* ---------- 增量更新（可选能力） ----------
     和 tools/sim/pack.py 配套。打开后，点「获取游戏」不再走模拟进度，
     而是真的按分块只下载变化的部分；下载 UI（圆环/速度/暂停/重试）照常工作。

     默认关闭：示例内容用模拟进度就够，需要真实分块下载时再打开。
     想验证真实增量更新时，把 enabled 改成 true，
     再起 tools/sim/serve.py 即可（详见 update-sim/README.md）。

       latestUrl      更新清单入口（换成你的 R2 地址即可上线）
       localManifest  本地清单；真实场景由宿主扫描安装目录生成
       localBase      演示用：从这里读"已安装内容"
       concurrency    并发下载的分块数
     ------------------------------------------ */
  updater: {
    enabled: false,
    latestUrl: 'sim/dist/latest.json',
    localManifest: 'sim/dist/manifests/v1-cdc.json',
    localBase: 'sim/v1/',
    concurrency: 6,
    retry: 3,
  },

  /* ---------- 设置弹窗 ----------
     几何对齐官方 .hyp-setting-dialog / .hyp-settings（左菜单 239px，整体高 480）。
     内容按官方启动器的实际分类整理；逻辑未实装，改值只更新本地状态。
     ---------------------------------- */
  settings: {
    title: '设置',
    appName: '示例启动器',
    version: '1.18.0.380',
    builder: 'HoYoPlay',
    appIcon: 'assets/icons/logo-app.svg',
    links: [
      { label: '用户协议' },
      { label: '隐私政策' },
      { label: '第三方开源许可' },
    ],
    copyright: '© miHoYo. 本页为界面复刻，功能尚未实装。',
    tabs: [
      {
        key: 'general', name: '常规',
        groups: [
          {
            title: '启动与运行',
            rows: [
              { type: 'switch', key: 'autoStart', label: '开机时自动启动', value: false },
              { type: 'switch', key: 'startMin', label: '启动后最小化到托盘', value: false },
              {
                type: 'switch', key: 'closeExit', label: '关闭主面板时退出启动器',
                hint: '关闭后启动器仍会在托盘中驻留', value: true,
              },
              {
                type: 'select', key: 'lang', label: '界面语言', value: '简体中文',
                options: ['简体中文', '繁體中文', 'English', '日本語', '한국어'],
              },
            ],
          },
          {
            title: '通知',
            rows: [
              { type: 'switch', key: 'notifyUpdate', label: '新版本可用时提醒', value: true },
              { type: 'switch', key: 'notifyActivity', label: '游戏活动提醒', value: true },
              { type: 'switch', key: 'notifyFriend', label: '好友消息提醒', value: false },
              {
                type: 'check', key: 'notifySound', text: '提示音',
                label: '通知方式', hint: '勾选后新消息会播放提示音', value: true,
              },
            ],
          },
        ],
      },
      {
        key: 'game', name: '游戏',
        groups: [
          {
            title: '安装',
            rows: [
              { type: 'static', label: '默认安装位置', value: 'F:\\miHoYo Launcher\\games' },
              { type: 'buttons', label: '目录操作',
                items: [{ text: '更改…', action: 'chooseDir' }] },
              { type: 'switch', key: 'autoInstall', label: '下载完成后自动安装', value: true },
              { type: 'switch', key: 'preDownload', label: '新版本自动预下载',
                hint: '下好后停在「待安装」，需要你点一下', value: false },
              {
                type: 'input', key: 'extraArgs', label: '附加启动参数',
                placeholder: '例如 -windowed -popupwindow', value: '',
              },
            ],
          },
          {
            title: '启动',
            rows: [
              { type: 'seg', key: 'launchMode', label: '启动方式', value: '全屏', options: ['全屏', '窗口', '无边框'] },
              { type: 'static', label: '启动参数', value: '（未设置）' },
              { type: 'buttons', label: '参数',
                items: [{ text: '编辑参数…', action: 'editArgs' }] },
            ],
          },
        ],
      },
      {
        key: 'download', name: '下载',
        groups: [
          {
            title: '传输',
            rows: [
              { type: 'slider', key: 'maxTask', label: '同时下载任务数', value: 3, min: 1, max: 8, unit: ' 个' },
              { type: 'slider', key: 'limitSpeed', label: '下载限速', value: 0, min: 0, max: 100, unit: ' MB/s' },
              { type: 'switch', key: 'p2p', label: '使用 P2P 加速', value: false },
            ],
          },
          {
            title: '缓存',
            rows: [
              { type: 'static', label: '下载缓存占用', key: 'cacheUsed', value: '12.6 GB' },
              { type: 'buttons', label: '缓存',
                items: [{ text: '清理缓存', action: 'clearCache' }] },
            ],
          },
        ],
      },
      {
        key: 'update', name: '更新', dot: true,
        groups: [
          {
            title: '启动器',
            rows: [
              { type: 'switch', key: 'autoCheck', label: '自动检查更新', value: true },
              { type: 'switch', key: 'reduceMotion', label: '减少界面动效',
                hint: '关闭呼吸、闪烁等循环动画', value: false },
              { type: 'static', label: '当前版本', value: '1.18.0.380' },
              { type: 'static', label: '前端版本', value: '1.18.2' },
              { type: 'static', label: '更新状态', key: 'updateStatus', value: '尚未检查' },
              { type: 'buttons', label: '更新',
                items: [{ text: '检查更新', action: 'checkUpdate', primary: true }] },
            ],
          },
        ],
      },
      {
        key: 'about', name: '关于',
        groups: [{ rows: [{ type: 'about' }] }],
      },
    ],
  },
};
