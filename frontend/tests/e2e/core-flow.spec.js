import { expect, test } from '@playwright/test'

const USERNAME_USER = 'e2e_user'
const USERNAME_ADMIN = 'e2e_admin'
const PASSWORD = 'E2Epass123!'

async function login(page, username) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill(username)
  await page.getByPlaceholder('密码').fill(PASSWORD)
  await page.getByRole('button', { name: '登录' }).click()
  await expect(page).toHaveURL(/\/$/)
  await expect(page.getByText(username)).toBeVisible()
}

test.describe('Auth & Guards', () => {
  test('unauthenticated user is redirected to /login', async ({ page }) => {
    await page.goto('/detect')
    await expect(page).toHaveURL(/\/login$/)
  })
})

test.describe('User Core Flow', () => {
  test('user can login and only sees image detection', async ({ page }) => {
    await login(page, USERNAME_USER)

    await page.goto('/detect')
    await expect(page.getByRole('button', { name: '视频检测' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: '摄像头检测' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: '开始检测' })).toBeVisible()
  })

  test('knowledge page and qna error state are available', async ({ page }) => {
    await login(page, USERNAME_USER)

    await page.goto('/knowledge')
    await expect(page.getByText('按作物、类别和特征检索病虫害知识条目')).toBeVisible()
    await expect(page.getByText('全部病虫害知识')).toBeVisible()

    await page.goto('/qna')
    await expect(page.getByText('基于知识库与检测上下文的辅助问答')).toBeVisible()

    await page.route('**/api/qna/ask', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: '模拟后端错误' })
      })
    })

    await page.getByPlaceholder('输入您的问题...').fill('测试问答失败态')
    await page.getByRole('button', { name: '发送' }).click()
    await expect(page.locator('.inline-error-card')).toContainText('模拟后端错误')
    await expect(page.getByRole('button', { name: '重试发送' })).toBeVisible()
  })
})

test.describe('Admin Core Flow', () => {
  test('admin can access admin routes and detect tabs', async ({ page }) => {
    await login(page, USERNAME_ADMIN)

    await page.goto('/detect')
    await expect(page.getByRole('button', { name: '图像检测' })).toBeVisible()
    await expect(page.getByRole('button', { name: '视频检测' })).toBeVisible()
    await expect(page.getByRole('button', { name: '摄像头检测' })).toBeVisible()

    await page.goto('/admin/overview')
    await expect(page.getByText('系统指标、检测结构与队列健康')).toBeVisible()

    await page.goto('/admin/configs')
    await expect(page.getByText('统一管理阈值、重试和队列相关参数')).toBeVisible()

    await page.goto('/admin/audit')
    await expect(page.getByText('查看 401/403 拒绝访问事件与来源信息')).toBeVisible()
  })
})
