<template>
  <comment-detail :is-edit="false" />
</template>

<script>
import CommentDetail from './components/CommentDetail'

export default {
  name: 'EditForm',
  components: { CommentDetail }
}
</script>

