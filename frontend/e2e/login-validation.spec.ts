import { test, expect } from "@playwright/test";

test("empty login shows validation messages without a request or runtime error", async ({ page }) => {
  const failures: string[] = [];
  const loginRequests: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("request", (request) => {
    if (request.url().includes("/auth/login")) loginRequests.push(request.url());
  });
  await page.goto(process.env.RADAR_E2E_URL || "http://127.0.0.1:5177");
  await page.getByRole("button", { name: "Enter workspace" }).click();
  await expect(page.getByText("Enter your username", { exact: true })).toBeVisible();
  await expect(page.getByText("Enter your password", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Enter workspace" })).toBeEnabled();
  expect(loginRequests).toEqual([]);
  expect(failures).toEqual([]);
});
