import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { writeFile } from "node:fs/promises";
test("login and primary workspace views pass automated WCAG checks", async ({
  page,
}) => {
  test.skip(
    !process.env.RADAR_E2E_USER || !process.env.RADAR_E2E_PASSWORD,
    "Credentials required",
  );
  await page.goto(process.env.RADAR_E2E_URL || "http://127.0.0.1:5177");
  const findings: { view: string; violations: unknown[] }[] = [];
  async function scan(view: string) {
    const r = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    findings.push({ view, violations: r.violations });
  }
  await scan("login");
  await page
    .getByLabel("Username", { exact: true })
    .fill(process.env.RADAR_E2E_USER!);
  await page
    .getByLabel("Password", { exact: true })
    .fill(process.env.RADAR_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Enter workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Transaction activity" }),
  ).toBeVisible();
  await scan("overview");
  await page.getByRole("button", { name: "Transactions", exact: true }).click();
  await expect(page.locator("tbody tr").first()).toBeVisible();
  await scan("transactions");
  await writeFile(
    "../reports/accessibility.json",
    JSON.stringify(findings, null, 2),
  );
  expect(
    findings.flatMap((f) => f.violations),
    "See reports/accessibility.json for rule/node evidence",
  ).toEqual([]);
});
