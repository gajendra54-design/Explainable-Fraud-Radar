import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("monitoring preserves an investigation and revokes logout", async ({
  page,
}) => {
  test.skip(
    !process.env.RADAR_E2E_USER || !process.env.RADAR_E2E_PASSWORD,
    "Credentials required",
  );
  await page.goto(process.env.RADAR_E2E_URL || "http://127.0.0.1:5177");
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
  await page.getByRole("button", { name: "Monitoring", exact: true }).click();
  await expect(
    page.getByText("Insufficient labels do not mean zero fraud"),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  const noLabels = await page.getByText("insufficient labels", {exact:true}).count(); if(noLabels) await expect(page.getByText("Not assessed",{exact:true}).first()).toBeVisible();
  await page.screenshot({path:"../reports/screenshots/monitoring.png",fullPage:true});
  const title = "Synthetic distribution review " + Date.now();
  await page.getByLabel("Title", { exact: true }).fill(title);
  await page
    .getByLabel("Investigation summary", { exact: true })
    .fill(
      "Automated synthetic monitoring workflow: inspect stored distribution evidence.",
    );
  await page
    .getByRole("button", { name: "Capture report & open investigation" })
    .click();
  await expect(
    page.getByRole("heading", { name: title, exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Investigation update", { exact: true })
    .fill(
      "Compared current feature distributions with the persisted reference report.",
    );
  await page
    .getByRole("button", { name: "Record investigation update" })
    .click();
  await expect(
    page.getByText(
      "Compared current feature distributions with the persisted reference report.",
    ),
  ).toBeVisible();
  await page
    .getByLabel("Investigation update", { exact: true })
    .fill(
      "Synthetic test investigation complete; no model promotion was performed.",
    );
  await page
    .getByRole("combobox", { name: "Next status", exact: true })
    .selectOption("Resolved");
  await page
    .getByLabel(
      "I confirm resolution; this investigation will become immutable.",
    )
    .check();
  await page
    .getByRole("button", { name: "Record investigation update" })
    .click();
  await expect(
    page.getByLabel("Investigation update", { exact: true }),
  ).toHaveCount(0);
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    result.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page.reload();
  await page.getByRole("button", { name: "Monitoring", exact: true }).click();
  await page.getByRole("button", { name: title, exact: true }).click();
  await expect(
    page.getByText(
      "Synthetic test investigation complete; no model promotion was performed.",
    ),
  ).toBeVisible();
  const oldToken = await page.evaluate(() =>
    sessionStorage.getItem("radar_token"),
  );
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome to your workspace" }),
  ).toBeVisible();
  const denied = await page.request.get(
    (process.env.RADAR_E2E_URL || "http://127.0.0.1:5177") + "/api/v1/auth/me",
    { headers: { Authorization: `Bearer ${oldToken}` } },
  );
  expect(denied.status()).toBe(401);
});
