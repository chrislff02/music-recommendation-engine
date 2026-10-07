#!/usr/bin/env -S node
import type { Contract as End } from '../../snapshots/9d1746249de938e6ce7b744e7854084fd60cb028ee49b1ca9d957279ce84141d/contract';
import endContract from '../../snapshots/9d1746249de938e6ce7b744e7854084fd60cb028ee49b1ca9d957279ce84141d/contract.json' with { type: 'json' };
import { Migration, MigrationCLI, col, fn, primaryKey } from '@prisma/orm-postgres/migration';

export default class M extends Migration<never, End> {
  override readonly endContractJson = endContract;

  override get operations() {
    return [
      this.createSchema({ schema: 'public' }),
      this.createTable({
        schema: 'public',
        table: 'Artist',
        columns: [
          col('id', 'SERIAL', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
          col('musicBrainzId', 'text', { codecRef: { codecId: 'pg/text@1' } }),
          col('name', 'text', { notNull: true, codecRef: { codecId: 'pg/text@1' } }),
        ],
        constraints: [primaryKey(['id'])],
      }),
      this.createTable({
        schema: 'public',
        table: 'Genre',
        columns: [
          col('id', 'SERIAL', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
          col('name', 'text', { notNull: true, codecRef: { codecId: 'pg/text@1' } }),
        ],
        constraints: [primaryKey(['id'])],
      }),
      this.createTable({
        schema: 'public',
        table: 'Rating',
        columns: [
          col('createdAt', 'timestamptz', {
            notNull: true,
            default: fn('now()'),
            codecRef: { codecId: 'pg/timestamptz-temporal@1' },
          }),
          col('id', 'SERIAL', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
          col('songId', 'int4', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
          col('updatedAt', 'timestamptz', {
            notNull: true,
            codecRef: { codecId: 'pg/timestamptz-temporal@1' },
          }),
          col('userId', 'int4', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
          col('value', 'int4', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
        ],
        constraints: [primaryKey(['id'])],
      }),
      this.createTable({
        schema: 'public',
        table: 'Song',
        columns: [
          col('acousticness', 'float8', { codecRef: { codecId: 'pg/float8@1' } }),
          col('artistId', 'int4', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
          col('createdAt', 'timestamptz', {
            notNull: true,
            default: fn('now()'),
            codecRef: { codecId: 'pg/timestamptz-temporal@1' },
          }),
          col('danceability', 'float8', { codecRef: { codecId: 'pg/float8@1' } }),
          col('duration', 'float8', { codecRef: { codecId: 'pg/float8@1' } }),
          col('energy', 'float8', { codecRef: { codecId: 'pg/float8@1' } }),
          col('externalId', 'text', { codecRef: { codecId: 'pg/text@1' } }),
          col('genreId', 'int4', { codecRef: { codecId: 'pg/int4@1' } }),
          col('id', 'SERIAL', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
          col('instrumentalness', 'float8', { codecRef: { codecId: 'pg/float8@1' } }),
          col('listenCount', 'int8', { codecRef: { codecId: 'pg/int8@1' } }),
          col('listenerCount', 'int4', { codecRef: { codecId: 'pg/int4@1' } }),
          col('liveness', 'float8', { codecRef: { codecId: 'pg/float8@1' } }),
          col('musicBrainzId', 'text', { codecRef: { codecId: 'pg/text@1' } }),
          col('popularity', 'float8', { codecRef: { codecId: 'pg/float8@1' } }),
          col('releaseYear', 'int4', { codecRef: { codecId: 'pg/int4@1' } }),
          col('speechiness', 'float8', { codecRef: { codecId: 'pg/float8@1' } }),
          col('tempo', 'float8', { codecRef: { codecId: 'pg/float8@1' } }),
          col('title', 'text', { notNull: true, codecRef: { codecId: 'pg/text@1' } }),
          col('updatedAt', 'timestamptz', {
            notNull: true,
            codecRef: { codecId: 'pg/timestamptz-temporal@1' },
          }),
          col('valence', 'float8', { codecRef: { codecId: 'pg/float8@1' } }),
        ],
        constraints: [primaryKey(['id'])],
      }),
      this.createTable({
        schema: 'public',
        table: 'User',
        columns: [
          col('createdAt', 'timestamptz', {
            notNull: true,
            default: fn('now()'),
            codecRef: { codecId: 'pg/timestamptz-temporal@1' },
          }),
          col('email', 'text', { notNull: true, codecRef: { codecId: 'pg/text@1' } }),
          col('id', 'SERIAL', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
          col('passwordHash', 'text', { notNull: true, codecRef: { codecId: 'pg/text@1' } }),
          col('updatedAt', 'timestamptz', {
            notNull: true,
            codecRef: { codecId: 'pg/timestamptz-temporal@1' },
          }),
          col('username', 'text', { notNull: true, codecRef: { codecId: 'pg/text@1' } }),
        ],
        constraints: [primaryKey(['id'])],
      }),
      this.createTable({
        schema: 'public',
        table: 'UserFavoriteArtist',
        columns: [
          col('artistId', 'int4', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
          col('createdAt', 'timestamptz', {
            notNull: true,
            default: fn('now()'),
            codecRef: { codecId: 'pg/timestamptz-temporal@1' },
          }),
          col('id', 'SERIAL', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
          col('userId', 'int4', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
        ],
        constraints: [primaryKey(['id'])],
      }),
      this.createTable({
        schema: 'public',
        table: 'UserFavoriteGenre',
        columns: [
          col('createdAt', 'timestamptz', {
            notNull: true,
            default: fn('now()'),
            codecRef: { codecId: 'pg/timestamptz-temporal@1' },
          }),
          col('genreId', 'int4', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
          col('id', 'SERIAL', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
          col('userId', 'int4', { notNull: true, codecRef: { codecId: 'pg/int4@1' } }),
        ],
        constraints: [primaryKey(['id'])],
      }),
      this.addUnique({
        schema: 'public',
        table: 'Artist',
        constraint: 'Artist_name_key',
        columns: ['name'],
      }),
      this.addUnique({
        schema: 'public',
        table: 'Artist',
        constraint: 'Artist_musicBrainzId_key',
        columns: ['musicBrainzId'],
      }),
      this.addUnique({
        schema: 'public',
        table: 'Genre',
        constraint: 'Genre_name_key',
        columns: ['name'],
      }),
      this.addUnique({
        schema: 'public',
        table: 'Rating',
        constraint: 'Rating_userId_songId_key',
        columns: ['userId', 'songId'],
      }),
      this.addUnique({
        schema: 'public',
        table: 'Song',
        constraint: 'Song_externalId_key',
        columns: ['externalId'],
      }),
      this.addUnique({
        schema: 'public',
        table: 'Song',
        constraint: 'Song_musicBrainzId_key',
        columns: ['musicBrainzId'],
      }),
      this.addUnique({
        schema: 'public',
        table: 'User',
        constraint: 'User_email_key',
        columns: ['email'],
      }),
      this.addUnique({
        schema: 'public',
        table: 'User',
        constraint: 'User_username_key',
        columns: ['username'],
      }),
      this.addUnique({
        schema: 'public',
        table: 'UserFavoriteArtist',
        constraint: 'UserFavoriteArtist_userId_artistId_key',
        columns: ['userId', 'artistId'],
      }),
      this.addUnique({
        schema: 'public',
        table: 'UserFavoriteGenre',
        constraint: 'UserFavoriteGenre_userId_genreId_key',
        columns: ['userId', 'genreId'],
      }),
      this.createIndex({
        schema: 'public',
        table: 'Rating',
        index: 'Rating_songId_idx_f4553cd5',
        columns: ['songId'],
      }),
      this.createIndex({
        schema: 'public',
        table: 'Rating',
        index: 'Rating_userId_idx_a489d58a',
        columns: ['userId'],
      }),
      this.createIndex({
        schema: 'public',
        table: 'Song',
        index: 'Song_artistId_idx_5a004db6',
        columns: ['artistId'],
      }),
      this.createIndex({
        schema: 'public',
        table: 'Song',
        index: 'Song_genreId_idx_8fce6a7b',
        columns: ['genreId'],
      }),
      this.createIndex({
        schema: 'public',
        table: 'Song',
        index: 'Song_releaseYear_idx_a285856b',
        columns: ['releaseYear'],
      }),
      this.createIndex({
        schema: 'public',
        table: 'Song',
        index: 'Song_title_idx_1c94c7b6',
        columns: ['title'],
      }),
      this.createIndex({
        schema: 'public',
        table: 'UserFavoriteArtist',
        index: 'UserFavoriteArtist_artistId_idx_5a004db6',
        columns: ['artistId'],
      }),
      this.createIndex({
        schema: 'public',
        table: 'UserFavoriteArtist',
        index: 'UserFavoriteArtist_userId_idx_a489d58a',
        columns: ['userId'],
      }),
      this.createIndex({
        schema: 'public',
        table: 'UserFavoriteGenre',
        index: 'UserFavoriteGenre_genreId_idx_8fce6a7b',
        columns: ['genreId'],
      }),
      this.createIndex({
        schema: 'public',
        table: 'UserFavoriteGenre',
        index: 'UserFavoriteGenre_userId_idx_a489d58a',
        columns: ['userId'],
      }),
      this.addForeignKey({
        schema: 'public',
        table: 'Rating',
        foreignKey: {
          name: 'Rating_userId_fkey',
          columns: ['userId'],
          references: { schema: 'public', table: 'User', columns: ['id'] },
          onDelete: 'cascade',
        },
      }),
      this.addForeignKey({
        schema: 'public',
        table: 'Rating',
        foreignKey: {
          name: 'Rating_songId_fkey',
          columns: ['songId'],
          references: { schema: 'public', table: 'Song', columns: ['id'] },
          onDelete: 'cascade',
        },
      }),
      this.addForeignKey({
        schema: 'public',
        table: 'Song',
        foreignKey: {
          name: 'Song_artistId_fkey',
          columns: ['artistId'],
          references: { schema: 'public', table: 'Artist', columns: ['id'] },
        },
      }),
      this.addForeignKey({
        schema: 'public',
        table: 'Song',
        foreignKey: {
          name: 'Song_genreId_fkey',
          columns: ['genreId'],
          references: { schema: 'public', table: 'Genre', columns: ['id'] },
        },
      }),
      this.addForeignKey({
        schema: 'public',
        table: 'UserFavoriteArtist',
        foreignKey: {
          name: 'UserFavoriteArtist_userId_fkey',
          columns: ['userId'],
          references: { schema: 'public', table: 'User', columns: ['id'] },
          onDelete: 'cascade',
        },
      }),
      this.addForeignKey({
        schema: 'public',
        table: 'UserFavoriteArtist',
        foreignKey: {
          name: 'UserFavoriteArtist_artistId_fkey',
          columns: ['artistId'],
          references: { schema: 'public', table: 'Artist', columns: ['id'] },
          onDelete: 'cascade',
        },
      }),
      this.addForeignKey({
        schema: 'public',
        table: 'UserFavoriteGenre',
        foreignKey: {
          name: 'UserFavoriteGenre_userId_fkey',
          columns: ['userId'],
          references: { schema: 'public', table: 'User', columns: ['id'] },
          onDelete: 'cascade',
        },
      }),
      this.addForeignKey({
        schema: 'public',
        table: 'UserFavoriteGenre',
        foreignKey: {
          name: 'UserFavoriteGenre_genreId_fkey',
          columns: ['genreId'],
          references: { schema: 'public', table: 'Genre', columns: ['id'] },
          onDelete: 'cascade',
        },
      }),
    ];
  }
}

MigrationCLI.run(import.meta.url, M);
