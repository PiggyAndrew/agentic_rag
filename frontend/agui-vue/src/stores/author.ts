import { defineStore } from 'pinia'

export interface AuthorProfile {
  name: string
  github: string
  email: string
  wechat: string
}

/**
 * 获取作者信息（静态配置），供 About 页面使用
 */
export const useAuthorStore = defineStore('author', {
  state: (): AuthorProfile => ({
    name: 'Andrew Yan',
    github: 'https://github.com/PiggyAndrew',
    email: 'andy.yan@cti-cert.com',
    wechat: 'modian4500',
  }),
})
