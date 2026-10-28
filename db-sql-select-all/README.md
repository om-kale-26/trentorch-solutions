# SELECT All Rows

Beginner | db

You are building the first page of a user-management dashboard. It must show every user's full profile (id, name, email, age) exactly as stored, with no filtering and no sorting.

Write a query that returns all rows and all columns from the `users` table.

### Constraints

- Return every row of `users`
- Return every column: id, name, email, age (in table order)
- No `WHERE` or `ORDER BY` is needed; row order does not matter

### Hints

<details>
<summary>Hint 1</summary>

`*` is shorthand for "all columns".

</details>

<details>
<summary>Hint 2</summary>

The table name goes after `FROM`. With no `WHERE`, every row is returned.

</details>
