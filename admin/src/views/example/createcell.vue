<template>
  <cell-detail :is-edit="false" />
</template>

<script>
import CellDetail from './components/CellDetail'

export default {
  name: 'CreateCell',
  components: { CellDetail }
}
</script>

